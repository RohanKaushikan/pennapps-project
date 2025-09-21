import React, { useRef, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Sphere, Text, OrbitControls, Image } from '@react-three/drei'
import * as THREE from 'three'

// Globe component with animation
function AnimatedGlobe({ 
  currentLocation, 
  targetCountry, 
  targetCountryPhoto,
  isAnimating, 
  onAnimationComplete,
  isSignedIn = false 
}) {
  const meshRef = useRef()
  const [rotation, setRotation] = useState([0, 0, 0])
  const [scale, setScale] = useState(1)
  const [animationPhase, setAnimationPhase] = useState('idle') // idle, zoomOut, spin, zoomIn
  const [showTargetPhoto, setShowTargetPhoto] = useState(false)

  useEffect(() => {
    if (!isAnimating) return

    const animate = async () => {
      // Phase 1: Zoom out from current location
      setAnimationPhase('zoomOut')
      await new Promise(resolve => {
        const startScale = 1
        const endScale = 0.3
        const duration = 1000
        const startTime = Date.now()

        const animateZoomOut = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const currentScale = startScale + (endScale - startScale) * progress
          setScale(currentScale)

          if (progress < 1) {
            requestAnimationFrame(animateZoomOut)
          } else {
            resolve()
          }
        }
        animateZoomOut()
      })

      // Phase 2: Spin to target country
      setAnimationPhase('spin')
      await new Promise(resolve => {
        const startRotation = [0, 0, 0]
        const targetRotation = targetCountry ? [
          (targetCountry.latitude * Math.PI) / 180,
          (targetCountry.longitude * Math.PI) / 180,
          0
        ] : [0, 0, 0]
        
        const duration = 2000
        const startTime = Date.now()

        const animateSpin = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const easeProgress = 1 - Math.pow(1 - progress, 3) // Ease out cubic
          
          const currentRotation = [
            startRotation[0] + (targetRotation[0] - startRotation[0]) * easeProgress,
            startRotation[1] + (targetRotation[1] - startRotation[1]) * easeProgress,
            startRotation[2] + (targetRotation[2] - startRotation[2]) * easeProgress
          ]
          setRotation(currentRotation)

          if (progress < 1) {
            requestAnimationFrame(animateSpin)
          } else {
            resolve()
          }
        }
        animateSpin()
      })

      // Phase 3: Show target country photo
      setAnimationPhase('zoomIn')
      setShowTargetPhoto(true)
      await new Promise(resolve => {
        const startScale = 0.3
        const endScale = 1.5
        const duration = 2000
        const startTime = Date.now()

        const animateZoomIn = () => {
          const elapsed = Date.now() - startTime
          const progress = Math.min(elapsed / duration, 1)
          const currentScale = startScale + (endScale - startScale) * progress
          setScale(currentScale)

          if (progress < 1) {
            requestAnimationFrame(animateZoomIn)
          } else {
            resolve()
          }
        }
        animateZoomIn()
      })

      setAnimationPhase('idle')
      onAnimationComplete?.()
    }

    animate()
  }, [isAnimating, targetCountry, onAnimationComplete])

  // Continuous rotation for non-signed-in users
  useFrame((state, delta) => {
    if (!isSignedIn && !isAnimating) {
      if (meshRef.current) {
        meshRef.current.rotation.y += delta * 0.2
      }
    }
  })

  return (
    <group ref={meshRef} rotation={rotation} scale={scale}>
      <Sphere args={[1, 64, 64]}>
        <meshPhongMaterial
          color="#4A90E2"
          transparent
          opacity={0.8}
          wireframe={false}
        />
      </Sphere>
      
      {/* Add some atmospheric glow */}
      <Sphere args={[1.02, 32, 32]}>
        <meshBasicMaterial
          color="#87CEEB"
          transparent
          opacity={0.1}
        />
      </Sphere>

      {/* Current location marker */}
      {currentLocation && (
        <group position={[
          Math.cos(currentLocation.longitude * Math.PI / 180) * Math.cos(currentLocation.latitude * Math.PI / 180),
          Math.sin(currentLocation.latitude * Math.PI / 180),
          Math.sin(currentLocation.longitude * Math.PI / 180) * Math.cos(currentLocation.latitude * Math.PI / 180)
        ]}>
          <Sphere args={[0.02, 8, 8]}>
            <meshBasicMaterial color="#FF6B6B" />
          </Sphere>
        </group>
      )}

      {/* Target country photo */}
      {targetCountry && targetCountryPhoto && showTargetPhoto && (
        <group position={[
          Math.cos(targetCountry.longitude * Math.PI / 180) * Math.cos(targetCountry.latitude * Math.PI / 180),
          Math.sin(targetCountry.latitude * Math.PI / 180),
          Math.sin(targetCountry.longitude * Math.PI / 180) * Math.cos(targetCountry.latitude * Math.PI / 180)
        ]}>
          <Image
            url={targetCountryPhoto}
            scale={[0.3, 0.2]}
            position={[0, 0, 0.1]}
            transparent
            opacity={0.9}
          />
        </group>
      )}

      {/* Target country marker (fallback) */}
      {targetCountry && !showTargetPhoto && (
        <group position={[
          Math.cos(targetCountry.longitude * Math.PI / 180) * Math.cos(targetCountry.latitude * Math.PI / 180),
          Math.sin(targetCountry.latitude * Math.PI / 180),
          Math.sin(targetCountry.longitude * Math.PI / 180) * Math.cos(targetCountry.latitude * Math.PI / 180)
        ]}>
          <Sphere args={[0.03, 8, 8]}>
            <meshBasicMaterial color="#4ECDC4" />
          </Sphere>
        </group>
      )}
    </group>
  )
}

// Main Globe component
export default function Globe({ 
  currentLocation, 
  targetCountry, 
  targetCountryPhoto,
  isAnimating, 
  onAnimationComplete,
  isSignedIn = false 
}) {
  return (
    <div className="w-full h-full">
      <Canvas
        camera={{ position: [0, 0, 3], fov: 75 }}
        style={{ background: 'transparent' }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <pointLight position={[-10, -10, -5]} intensity={0.5} />
        
        <AnimatedGlobe
          currentLocation={currentLocation}
          targetCountry={targetCountry}
          targetCountryPhoto={targetCountryPhoto}
          isAnimating={isAnimating}
          onAnimationComplete={onAnimationComplete}
          isSignedIn={isSignedIn}
        />
        
        <OrbitControls
          enableZoom={false}
          enablePan={false}
          enableRotate={!isAnimating}
          autoRotate={!isSignedIn && !isAnimating}
          autoRotateSpeed={0.5}
        />
      </Canvas>
    </div>
  )
}
