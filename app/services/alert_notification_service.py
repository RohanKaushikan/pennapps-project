import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.location_event import LocationAlert, AlertSeverity

logger = structlog.get_logger(__name__)


class NotificationChannel:
    """Base class for notification channels."""

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification through this channel."""
        raise NotImplementedError


class PushNotificationChannel(NotificationChannel):
    """Push notification channel for mobile devices."""

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send push notification."""
        try:
            # In a real implementation, this would integrate with FCM, APNs, etc.
            logger.info(
                "Sending push notification",
                user_id=user_id,
                title=title,
                priority=priority
            )

            # Simulate notification sending
            await asyncio.sleep(0.1)  # Simulate network delay

            return True

        except Exception as e:
            logger.error("Error sending push notification", error=str(e), user_id=user_id)
            return False


class SMSNotificationChannel(NotificationChannel):
    """SMS notification channel for high-priority alerts."""

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send SMS notification."""
        try:
            # In a real implementation, this would integrate with Twilio, AWS SNS, etc.
            logger.info(
                "Sending SMS notification",
                user_id=user_id,
                title=title,
                priority=priority
            )

            # Simulate SMS sending
            await asyncio.sleep(0.2)  # Simulate network delay

            return True

        except Exception as e:
            logger.error("Error sending SMS notification", error=str(e), user_id=user_id)
            return False


class EmailNotificationChannel(NotificationChannel):
    """Email notification channel for detailed alerts."""

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send email notification."""
        try:
            # In a real implementation, this would integrate with SendGrid, AWS SES, etc.
            logger.info(
                "Sending email notification",
                user_id=user_id,
                title=title,
                priority=priority
            )

            # Simulate email sending
            await asyncio.sleep(0.3)  # Simulate network delay

            return True

        except Exception as e:
            logger.error("Error sending email notification", error=str(e), user_id=user_id)
            return False


class WebSocketNotificationChannel(NotificationChannel):
    """WebSocket notification channel for real-time updates."""

    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send WebSocket notification."""
        try:
            # In a real implementation, this would send through active WebSocket connections
            logger.info(
                "Sending WebSocket notification",
                user_id=user_id,
                title=title,
                priority=priority
            )

            # Simulate WebSocket sending
            await asyncio.sleep(0.05)  # Simulate minimal delay

            return True

        except Exception as e:
            logger.error("Error sending WebSocket notification", error=str(e), user_id=user_id)
            return False


class AlertNotificationService:
    """
    Service for sending location-based alerts through multiple notification channels.

    Handles immediate delivery, priority routing, and delivery tracking for
    location-triggered alerts and emergency broadcasts.
    """

    def __init__(self):
        self.channels = {
            "push": PushNotificationChannel(),
            "sms": SMSNotificationChannel(),
            "email": EmailNotificationChannel(),
            "websocket": WebSocketNotificationChannel()
        }

        # Priority configuration for different alert types
        self.priority_config = {
            AlertSeverity.CRITICAL: {
                "channels": ["push", "sms", "websocket"],
                "retry_attempts": 3,
                "retry_delay": 5
            },
            AlertSeverity.HIGH: {
                "channels": ["push", "websocket"],
                "retry_attempts": 2,
                "retry_delay": 10
            },
            AlertSeverity.MEDIUM: {
                "channels": ["push", "websocket"],
                "retry_attempts": 1,
                "retry_delay": 30
            },
            AlertSeverity.LOW: {
                "channels": ["push"],
                "retry_attempts": 1,
                "retry_delay": 60
            }
        }

    async def send_alert_notification(self, alert: LocationAlert) -> Dict[str, Any]:
        """
        Send notification for a location alert.

        Args:
            alert: LocationAlert instance to send

        Returns:
            Delivery result with status and details
        """
        try:
            # Get priority configuration
            priority_config = self.priority_config.get(
                alert.severity,
                self.priority_config[AlertSeverity.LOW]
            )

            # Prepare notification content
            notification_data = {
                "title": alert.title,
                "message": alert.message,
                "metadata": {
                    "alert_id": str(alert.id),
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "country_code": alert.country_code,
                    "source": alert.source,
                    "location_data": alert.location_data
                }
            }

            # Send through configured channels
            delivery_results = {}
            successful_channels = []

            for channel_name in priority_config["channels"]:
                if channel_name in self.channels:
                    success = await self._send_with_retry(
                        channel_name,
                        alert.user_id,
                        notification_data,
                        priority_config["retry_attempts"],
                        priority_config["retry_delay"]
                    )

                    delivery_results[channel_name] = success
                    if success:
                        successful_channels.append(channel_name)

            # Update alert delivery status
            async with get_session() as session:
                if successful_channels:
                    alert.sent_at = datetime.utcnow()
                    alert.delivered_at = datetime.utcnow()

                    await session.execute(
                        update(LocationAlert)
                        .where(LocationAlert.id == alert.id)
                        .values(
                            sent_at=alert.sent_at,
                            delivered_at=alert.delivered_at
                        )
                    )
                    await session.commit()

            logger.info(
                "Alert notification sent",
                alert_id=str(alert.id),
                user_id=alert.user_id,
                severity=alert.severity.value,
                successful_channels=successful_channels,
                delivery_results=delivery_results
            )

            return {
                "success": len(successful_channels) > 0,
                "alert_id": str(alert.id),
                "channels_attempted": list(delivery_results.keys()),
                "channels_successful": successful_channels,
                "delivery_results": delivery_results
            }

        except Exception as e:
            logger.error(
                "Error sending alert notification",
                alert_id=str(alert.id) if alert else None,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def send_emergency_notification(self, alert: LocationAlert) -> Dict[str, Any]:
        """
        Send high-priority emergency notification with all available channels.

        Args:
            alert: Emergency LocationAlert instance

        Returns:
            Emergency delivery result
        """
        try:
            # Use all available channels for emergency notifications
            emergency_channels = ["push", "sms", "websocket", "email"]

            notification_data = {
                "title": f"🚨 EMERGENCY: {alert.title}",
                "message": f"URGENT: {alert.message}",
                "metadata": {
                    "alert_id": str(alert.id),
                    "alert_type": alert.alert_type.value,
                    "severity": "EMERGENCY",
                    "country_code": alert.country_code,
                    "source": alert.source,
                    "emergency": True,
                    "location_data": alert.location_data
                }
            }

            # Send simultaneously through all channels
            tasks = []
            for channel_name in emergency_channels:
                if channel_name in self.channels:
                    task = self._send_with_retry(
                        channel_name,
                        alert.user_id,
                        notification_data,
                        retry_attempts=3,
                        retry_delay=2  # Faster retry for emergencies
                    )
                    tasks.append((channel_name, task))

            # Execute all notifications concurrently
            results = await asyncio.gather(
                *[task for _, task in tasks],
                return_exceptions=True
            )

            # Process results
            delivery_results = {}
            successful_channels = []

            for i, (channel_name, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    delivery_results[channel_name] = False
                    logger.error(
                        "Emergency notification failed",
                        channel=channel_name,
                        error=str(result)
                    )
                else:
                    delivery_results[channel_name] = result
                    if result:
                        successful_channels.append(channel_name)

            # Update alert status
            async with get_session() as session:
                current_time = datetime.utcnow()
                await session.execute(
                    update(LocationAlert)
                    .where(LocationAlert.id == alert.id)
                    .values(
                        sent_at=current_time,
                        delivered_at=current_time if successful_channels else None
                    )
                )
                await session.commit()

            logger.critical(
                "Emergency notification sent",
                alert_id=str(alert.id),
                user_id=alert.user_id,
                successful_channels=successful_channels,
                total_channels=len(emergency_channels)
            )

            return {
                "success": len(successful_channels) > 0,
                "alert_id": str(alert.id),
                "emergency": True,
                "channels_attempted": emergency_channels,
                "channels_successful": successful_channels,
                "delivery_results": delivery_results
            }

        except Exception as e:
            logger.error(
                "Error sending emergency notification",
                alert_id=str(alert.id) if alert else None,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "emergency": True
            }

    async def send_bulk_notifications(
        self,
        alerts: List[LocationAlert],
        max_concurrent: int = 50
    ) -> Dict[str, Any]:
        """
        Send notifications for multiple alerts concurrently.

        Args:
            alerts: List of LocationAlert instances
            max_concurrent: Maximum concurrent notifications

        Returns:
            Bulk delivery results
        """
        try:
            # Process alerts in batches to avoid overwhelming notification services
            results = []
            failed_alerts = []

            # Create semaphore to limit concurrent operations
            semaphore = asyncio.Semaphore(max_concurrent)

            async def send_single_alert(alert):
                async with semaphore:
                    return await self.send_alert_notification(alert)

            # Process alerts in batches
            batch_size = max_concurrent
            for i in range(0, len(alerts), batch_size):
                batch = alerts[i:i + batch_size]
                batch_tasks = [send_single_alert(alert) for alert in batch]

                batch_results = await asyncio.gather(
                    *batch_tasks,
                    return_exceptions=True
                )

                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        failed_alerts.append({
                            "alert_id": str(batch[j].id),
                            "error": str(result)
                        })
                    else:
                        results.append(result)

                # Small delay between batches to be respectful to notification services
                if i + batch_size < len(alerts):
                    await asyncio.sleep(0.1)

            successful_notifications = len([r for r in results if r.get("success")])

            logger.info(
                "Bulk notifications completed",
                total_alerts=len(alerts),
                successful=successful_notifications,
                failed=len(failed_alerts)
            )

            return {
                "success": len(failed_alerts) == 0,
                "total_alerts": len(alerts),
                "successful_notifications": successful_notifications,
                "failed_notifications": len(failed_alerts),
                "results": results,
                "failed_alerts": failed_alerts
            }

        except Exception as e:
            logger.error("Error sending bulk notifications", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "total_alerts": len(alerts) if alerts else 0
            }

    async def _send_with_retry(
        self,
        channel_name: str,
        user_id: str,
        notification_data: Dict[str, Any],
        retry_attempts: int,
        retry_delay: int
    ) -> bool:
        """Send notification with retry logic."""
        channel = self.channels.get(channel_name)
        if not channel:
            return False

        for attempt in range(retry_attempts):
            try:
                success = await channel.send_notification(
                    user_id=user_id,
                    title=notification_data["title"],
                    message=notification_data["message"],
                    priority=notification_data.get("metadata", {}).get("severity", "normal"),
                    metadata=notification_data.get("metadata")
                )

                if success:
                    return True

                # If not successful and we have more attempts, wait and retry
                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)

            except Exception as e:
                logger.warning(
                    "Notification attempt failed",
                    channel=channel_name,
                    attempt=attempt + 1,
                    error=str(e)
                )

                if attempt < retry_attempts - 1:
                    await asyncio.sleep(retry_delay)

        return False

    def configure_channel_priority(
        self,
        severity: AlertSeverity,
        channels: List[str],
        retry_attempts: int = 1,
        retry_delay: int = 30
    ):
        """
        Configure notification channels for a specific alert severity.

        Args:
            severity: Alert severity level
            channels: List of channel names to use
            retry_attempts: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.priority_config[severity] = {
            "channels": channels,
            "retry_attempts": retry_attempts,
            "retry_delay": retry_delay
        }

        logger.info(
            "Channel priority configured",
            severity=severity.value,
            channels=channels,
            retry_attempts=retry_attempts
        )

    def add_notification_channel(self, name: str, channel: NotificationChannel):
        """Add a new notification channel."""
        self.channels[name] = channel
        logger.info("Notification channel added", channel_name=name)

    def remove_notification_channel(self, name: str):
        """Remove a notification channel."""
        if name in self.channels:
            del self.channels[name]
            logger.info("Notification channel removed", channel_name=name)

    async def get_delivery_stats(self, time_period_hours: int = 24) -> Dict[str, Any]:
        """
        Get notification delivery statistics.

        Args:
            time_period_hours: Time period to analyze

        Returns:
            Delivery statistics
        """
        try:
            async with get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=time_period_hours)

                # Get alerts in time period
                alerts_query = select(LocationAlert).where(
                    LocationAlert.created_at >= cutoff_time
                )
                alerts_result = await session.execute(alerts_query)
                alerts = alerts_result.scalars().all()

                total_alerts = len(alerts)
                sent_alerts = len([a for a in alerts if a.sent_at])
                delivered_alerts = len([a for a in alerts if a.delivered_at])
                read_alerts = len([a for a in alerts if a.read_at])

                # Calculate stats by severity
                severity_stats = {}
                for severity in AlertSeverity:
                    severity_alerts = [a for a in alerts if a.severity == severity]
                    severity_stats[severity.value] = {
                        "total": len(severity_alerts),
                        "sent": len([a for a in severity_alerts if a.sent_at]),
                        "delivered": len([a for a in severity_alerts if a.delivered_at]),
                        "read": len([a for a in severity_alerts if a.read_at])
                    }

                return {
                    "time_period_hours": time_period_hours,
                    "total_alerts": total_alerts,
                    "sent_alerts": sent_alerts,
                    "delivered_alerts": delivered_alerts,
                    "read_alerts": read_alerts,
                    "delivery_rate": (delivered_alerts / total_alerts * 100) if total_alerts > 0 else 0,
                    "read_rate": (read_alerts / delivered_alerts * 100) if delivered_alerts > 0 else 0,
                    "severity_stats": severity_stats
                }

        except Exception as e:
            logger.error("Error getting delivery stats", error=str(e))
            return {"error": str(e)}