import asyncio
import threading
import time
import sqlite3
import hashlib
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

from nlp_processor import NLPProcessor
from legal_analyzer import LegalTextAnalyzer
from alert_enhancer import AlertEnhancer

@dataclass
class ProcessingJob:
    alert_id: str
    content: str
    job_type: str  # 'new', 'update', 'retry'
    created_at: datetime
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class ProcessingStats:
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: datetime = None

class AlertMonitor:
    def __init__(self, db_path: str, nlp_processor: NLPProcessor,
                 legal_analyzer: LegalTextAnalyzer, alert_enhancer: AlertEnhancer):
        self.db_path = db_path
        self.nlp_processor = nlp_processor
        self.legal_analyzer = legal_analyzer
        self.alert_enhancer = alert_enhancer

        # Monitoring state
        self.last_check_time = datetime.now()
        self.processed_alerts: Set[str] = set()
        self.content_hashes: Dict[str, str] = {}
        self.processing_queue = asyncio.Queue()
        self.stats = ProcessingStats()

        # Configuration
        self.check_interval = 30  # seconds
        self.batch_size = 10
        self.max_queue_size = 100

        # Background task control
        self.is_running = False
        self.monitor_task = None
        self.processor_task = None

        # Logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content change detection"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _load_processed_alerts(self):
        """Load previously processed alerts from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Load from alert_intelligence table
                cursor = conn.execute('SELECT alert_id FROM alert_intelligence')
                nlp_processed = {row[0] for row in cursor.fetchall()}

                # Load from alert_legal_analysis table
                cursor = conn.execute('SELECT DISTINCT alert_id FROM alert_legal_analysis')
                legal_processed = {row[0] for row in cursor.fetchall()}

                # Combine both sets
                self.processed_alerts = nlp_processed.intersection(legal_processed)
                self.logger.info(f"Loaded {len(self.processed_alerts)} previously processed alerts")

        except Exception as e:
            self.logger.error(f"Error loading processed alerts: {e}")

    def _get_new_alerts(self) -> List[Dict]:
        """Get new alerts since last check"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, title, timestamp, country_code
                    FROM news_items
                    WHERE timestamp > ?
                    ORDER BY timestamp ASC
                    LIMIT ?
                ''', (self.last_check_time.isoformat(), self.batch_size))

                alerts = []
                for row in cursor.fetchall():
                    alerts.append({
                        'id': row[0],
                        'title': row[1],
                        'timestamp': row[2],
                        'country_code': row[3]
                    })

                return alerts

        except Exception as e:
            self.logger.error(f"Error getting new alerts: {e}")
            return []

    def _get_updated_alerts(self) -> List[Dict]:
        """Detect alerts with changed content"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, title, timestamp, country_code
                    FROM news_items
                    WHERE id IN ({})
                '''.format(','.join('?' * len(self.processed_alerts))),
                list(self.processed_alerts))

                updated_alerts = []
                for row in cursor.fetchall():
                    alert_id, title, timestamp, country_code = row
                    current_hash = self._get_content_hash(title)

                    # Check if content has changed
                    if alert_id in self.content_hashes:
                        if self.content_hashes[alert_id] != current_hash:
                            updated_alerts.append({
                                'id': alert_id,
                                'title': title,
                                'timestamp': timestamp,
                                'country_code': country_code
                            })
                            self.content_hashes[alert_id] = current_hash
                    else:
                        # Store hash for future comparison
                        self.content_hashes[alert_id] = current_hash

                return updated_alerts

        except Exception as e:
            self.logger.error(f"Error detecting updated alerts: {e}")
            return []

    async def _queue_processing_job(self, alert: Dict, job_type: str = 'new'):
        """Queue an alert for processing"""
        if self.processing_queue.qsize() >= self.max_queue_size:
            self.logger.warning("Processing queue is full, skipping alert")
            return

        job = ProcessingJob(
            alert_id=alert['id'],
            content=alert['title'],
            job_type=job_type,
            created_at=datetime.now()
        )

        await self.processing_queue.put(job)
        self.logger.debug(f"Queued {job_type} job for alert {alert['id']}")

    async def _process_alert_job(self, job: ProcessingJob) -> bool:
        """Process a single alert with ML intelligence"""
        try:
            self.logger.info(f"Processing {job.job_type} alert {job.alert_id}")

            # Check if already processed (avoid duplicates)
            if job.job_type == 'new' and job.alert_id in self.processed_alerts:
                self.stats.skipped += 1
                return True

            # Process with NLP
            try:
                nlp_intelligence = self.nlp_processor.process_alert_content(
                    alert_id=job.alert_id,
                    content=job.content
                )
                self._store_alert_intelligence(nlp_intelligence)

            except Exception as e:
                self.logger.error(f"NLP processing failed for {job.alert_id}: {e}")
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    await self.processing_queue.put(job)
                    return False
                raise

            # Process with legal analyzer
            try:
                legal_analysis = self.legal_analyzer.analyze_alert_content(
                    alert_id=job.alert_id,
                    content=job.content
                )
                self._store_legal_analysis(legal_analysis)

            except Exception as e:
                self.logger.error(f"Legal analysis failed for {job.alert_id}: {e}")
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    await self.processing_queue.put(job)
                    return False
                raise

            # Mark as processed
            self.processed_alerts.add(job.alert_id)
            self.content_hashes[job.alert_id] = self._get_content_hash(job.content)

            self.stats.successful += 1
            self.logger.info(f"Successfully processed alert {job.alert_id}")
            return True

        except Exception as e:
            self.logger.error(f"Processing failed for alert {job.alert_id}: {e}")
            self.stats.failed += 1
            return False

    def _store_alert_intelligence(self, intelligence):
        """Store NLP intelligence in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO alert_intelligence (
                    alert_id, legal_requirements, recommendations, effective_dates,
                    deadlines, penalties, document_requirements, compliance_urgency,
                    requirement_keywords, legal_language_keywords, time_indicators,
                    legal_classification, risk_level, traveler_impact, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                intelligence.alert_id,
                json.dumps(intelligence.legal_requirements),
                json.dumps(intelligence.recommendations),
                json.dumps(intelligence.effective_dates),
                json.dumps(intelligence.deadlines),
                json.dumps(intelligence.penalties),
                json.dumps(intelligence.document_requirements),
                intelligence.compliance_urgency,
                json.dumps(intelligence.requirement_keywords),
                json.dumps(intelligence.legal_language_keywords),
                json.dumps(intelligence.time_indicators),
                intelligence.legal_classification,
                intelligence.risk_level,
                intelligence.traveler_impact,
                intelligence.created_at
            ))
            conn.commit()

    def _store_legal_analysis(self, analysis):
        """Store legal analysis in database"""
        with sqlite3.connect(self.db_path) as conn:
            # Store summary record
            conn.execute('''
                INSERT OR REPLACE INTO alert_legal_analysis (
                    alert_id, requirement_text, requirement_type, penalty_severity,
                    compliance_deadline, legal_authority, enforcement_likelihood,
                    fine_amount, document_validity_period, entry_exit_specific,
                    overall_severity, critical_deadlines, mandatory_documents,
                    penalty_summary, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.alert_id,
                'SUMMARY',
                'summary',
                analysis.overall_severity,
                None, None, 'high', None, None, 'both',
                analysis.overall_severity,
                json.dumps(analysis.critical_deadlines),
                json.dumps(analysis.mandatory_documents),
                analysis.penalty_summary,
                analysis.created_at
            ))

            # Store individual requirements
            for req in analysis.requirements:
                conn.execute('''
                    INSERT OR REPLACE INTO alert_legal_analysis (
                        alert_id, requirement_text, requirement_type, penalty_severity,
                        compliance_deadline, legal_authority, enforcement_likelihood,
                        fine_amount, document_validity_period, entry_exit_specific,
                        overall_severity, critical_deadlines, mandatory_documents,
                        penalty_summary, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    analysis.alert_id, req.requirement_text, req.requirement_type,
                    req.penalty_severity, req.compliance_deadline, req.legal_authority,
                    req.enforcement_likelihood, req.fine_amount, req.document_validity_period,
                    req.entry_exit_specific, analysis.overall_severity,
                    json.dumps(analysis.critical_deadlines),
                    json.dumps(analysis.mandatory_documents),
                    analysis.penalty_summary, analysis.created_at
                ))
            conn.commit()

    async def _monitor_alerts(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Get new alerts
                new_alerts = self._get_new_alerts()
                for alert in new_alerts:
                    await self._queue_processing_job(alert, 'new')

                # Check for updated alerts
                updated_alerts = self._get_updated_alerts()
                for alert in updated_alerts:
                    await self._queue_processing_job(alert, 'update')

                # Update last check time
                self.last_check_time = datetime.now()

                # Log stats periodically
                if self.stats.total_processed % 10 == 0 and self.stats.total_processed > 0:
                    self._log_stats()

                # Wait for next check
                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(self.check_interval)

    async def _process_queue(self):
        """Main processing loop"""
        while self.is_running:
            try:
                # Get job from queue (with timeout)
                job = await asyncio.wait_for(
                    self.processing_queue.get(),
                    timeout=self.check_interval
                )

                # Process the job
                success = await self._process_alert_job(job)
                self.stats.total_processed += 1

                # Mark task as done
                self.processing_queue.task_done()

            except asyncio.TimeoutError:
                # No jobs in queue, continue
                continue
            except Exception as e:
                self.logger.error(f"Processing loop error: {e}")

    def _log_stats(self):
        """Log processing statistics"""
        if self.stats.start_time:
            runtime = datetime.now() - self.stats.start_time
            rate = self.stats.total_processed / runtime.total_seconds() * 60  # per minute

            self.logger.info(
                f"Processing stats: {self.stats.successful} successful, "
                f"{self.stats.failed} failed, {self.stats.skipped} skipped, "
                f"{rate:.1f} alerts/min, queue size: {self.processing_queue.qsize()}"
            )

    async def start(self):
        """Start the background monitoring and processing"""
        if self.is_running:
            self.logger.warning("Background processor already running")
            return

        self.logger.info("Starting background alert processor")
        self.is_running = True
        self.stats.start_time = datetime.now()

        # Load existing processed alerts
        self._load_processed_alerts()

        # Start monitoring and processing tasks
        self.monitor_task = asyncio.create_task(self._monitor_alerts())
        self.processor_task = asyncio.create_task(self._process_queue())

        self.logger.info("Background processor started successfully")

    async def stop(self):
        """Stop the background processing"""
        if not self.is_running:
            return

        self.logger.info("Stopping background alert processor")
        self.is_running = False

        # Cancel tasks
        if self.monitor_task:
            self.monitor_task.cancel()
        if self.processor_task:
            self.processor_task.cancel()

        # Wait for queue to finish
        await self.processing_queue.join()

        # Log final stats
        self._log_stats()
        self.logger.info("Background processor stopped")

    def get_status(self) -> Dict:
        """Get current status and statistics"""
        return {
            'is_running': self.is_running,
            'processed_alerts_count': len(self.processed_alerts),
            'queue_size': self.processing_queue.qsize(),
            'stats': {
                'total_processed': self.stats.total_processed,
                'successful': self.stats.successful,
                'failed': self.stats.failed,
                'skipped': self.stats.skipped,
                'start_time': self.stats.start_time.isoformat() if self.stats.start_time else None,
                'runtime_minutes': (datetime.now() - self.stats.start_time).total_seconds() / 60 if self.stats.start_time else 0
            },
            'configuration': {
                'check_interval': self.check_interval,
                'batch_size': self.batch_size,
                'max_queue_size': self.max_queue_size
            }
        }

class BackgroundProcessor:
    """Main background processor coordinator"""

    def __init__(self, db_path: str):
        self.db_path = db_path

        # Initialize ML components
        self.nlp_processor = NLPProcessor()
        self.legal_analyzer = LegalTextAnalyzer()
        self.alert_enhancer = AlertEnhancer(self.nlp_processor, self.legal_analyzer)

        # Initialize monitor
        self.monitor = AlertMonitor(
            db_path, self.nlp_processor,
            self.legal_analyzer, self.alert_enhancer
        )

        # Threading for integration with existing sync app
        self.thread = None
        self.loop = None

    def start_background_processing(self):
        """Start background processing in a separate thread"""
        if self.thread and self.thread.is_alive():
            return

        def run_async_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self.monitor.start())
                self.loop.run_forever()
            except Exception as e:
                print(f"Background processing error: {e}")
            finally:
                self.loop.close()

        self.thread = threading.Thread(target=run_async_loop, daemon=True)
        self.thread.start()

    def stop_background_processing(self):
        """Stop background processing"""
        if self.loop and not self.loop.is_closed():
            asyncio.run_coroutine_threadsafe(self.monitor.stop(), self.loop)
            self.loop.call_soon_threadsafe(self.loop.stop)

    def get_status(self) -> Dict:
        """Get processing status"""
        return self.monitor.get_status()