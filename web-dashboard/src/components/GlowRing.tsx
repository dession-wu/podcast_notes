"use client";

import { useEffect, useRef, useCallback } from "react";

export type GlowMode = "flow" | "pulse" | "orbit";

interface GlowRingProps {
  mode?: GlowMode;
  className?: string;
}

export default function GlowRing({ mode = "flow", className = "" }: GlowRingProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);
  const modeRef = useRef<GlowMode>(mode);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    }

    const width = rect.width;
    const height = rect.height;
    const centerX = width * 0.15;
    const centerY = height * 0.5;
    const radius = Math.min(width, height) * 0.55;

    ctx.clearRect(0, 0, width, height);

    const currentMode = modeRef.current;
    const time = Date.now() / 1000;

    const startAngle = -Math.PI * 0.8;
    const endAngle = Math.PI * 0.8;

    if (currentMode === "flow") {
      drawFlowMode(ctx, centerX, centerY, radius, startAngle, endAngle, time);
    } else if (currentMode === "pulse") {
      drawPulseMode(ctx, centerX, centerY, radius, startAngle, endAngle, time);
    } else if (currentMode === "orbit") {
      drawOrbitMode(ctx, centerX, centerY, radius, startAngle, endAngle, time);
    }

    animationRef.current = requestAnimationFrame(draw);
  }, []);

  useEffect(() => {
    animationRef.current = requestAnimationFrame(draw);
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [draw]);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
      style={{ opacity: 0.9 }}
    />
  );
}

// ============ Flow Mode: Particles with boundary reflection ============
function drawFlowMode(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  time: number
) {
  const arcLength = endAngle - startAngle;

  // Base ring with subtle gradient
  drawArcGlow(ctx, cx, cy, r, startAngle, endAngle, [
    { offset: 0, color: "rgba(99, 102, 241, 0.06)" },
    { offset: 0.5, color: "rgba(129, 140, 248, 0.1)" },
    { offset: 1, color: "rgba(99, 102, 241, 0.06)" },
  ], 6);

  // Particles with boundary reflection physics
  const particles = [
    { id: 1, speed: 0.25, offset: 0, size: 1.0, color: "#c7d2fe", phase: 0 },
    { id: 2, speed: 0.4, offset: 0.2, size: 0.7, color: "#818cf8", phase: Math.PI * 0.5 },
    { id: 3, speed: 0.15, offset: 0.5, size: 0.85, color: "#a5b4fc", phase: Math.PI },
    { id: 4, speed: 0.35, offset: 0.75, size: 0.6, color: "#6366f1", phase: Math.PI * 1.5 },
  ];

  particles.forEach((particle) => {
    // Use sine wave for back-and-forth motion within arc boundaries
    const rawPos = Math.sin(time * particle.speed + particle.phase);
    const normalizedPos = (rawPos + 1) / 2; // Map -1..1 to 0..1
    const angle = startAngle + arcLength * normalizedPos;

    const px = cx + Math.cos(angle) * r;
    const py = cy + Math.sin(angle) * r;

    const baseSize = 20 * particle.size;

    // Glow with boundary intensity (brighter at endpoints)
    const boundaryIntensity = 1 - Math.abs(rawPos) * 0.3;

    // Outer glow
    const outerGradient = ctx.createRadialGradient(px, py, 0, px, py, baseSize * 3);
    outerGradient.addColorStop(0, hexToRgba(particle.color, 0.6 * boundaryIntensity));
    outerGradient.addColorStop(0.3, hexToRgba(particle.color, 0.25 * boundaryIntensity));
    outerGradient.addColorStop(1, "rgba(99, 102, 241, 0)");

    ctx.fillStyle = outerGradient;
    ctx.fillRect(px - baseSize * 3, py - baseSize * 3, baseSize * 6, baseSize * 6);

    // Core bright spot
    const coreGradient = ctx.createRadialGradient(px, py, 0, px, py, baseSize);
    coreGradient.addColorStop(0, `rgba(255, 255, 255, ${0.9 * boundaryIntensity})`);
    coreGradient.addColorStop(0.5, hexToRgba(particle.color, 0.5 * boundaryIntensity));
    coreGradient.addColorStop(1, hexToRgba(particle.color, 0));

    ctx.fillStyle = coreGradient;
    ctx.fillRect(px - baseSize, py - baseSize, baseSize * 2, baseSize * 2);

    // Draw motion trail based on velocity direction
    const velocity = Math.cos(time * particle.speed + particle.phase);
    const trailLength = Math.abs(velocity) * 0.12;
    const trailDir = velocity > 0 ? 1 : -1;

    if (trailLength > 0.02) {
      const trailStart = normalizedPos;
      const trailEnd = Math.max(0, Math.min(1, normalizedPos - trailLength * trailDir));

      const trailStartAngle = startAngle + arcLength * trailStart;
      const trailEndAngle = startAngle + arcLength * trailEnd;

      drawArcGlow(ctx, cx, cy, r, Math.min(trailStartAngle, trailEndAngle), Math.max(trailStartAngle, trailEndAngle), [
        { offset: 0, color: hexToRgba(particle.color, 0) },
        { offset: 0.5, color: hexToRgba(particle.color, 0.2 * boundaryIntensity) },
        { offset: 1, color: hexToRgba(particle.color, 0) },
      ], 3 * particle.size);
    }
  });
}

// ============ Pulse Mode: Radial breathing with boundary rings ============
function drawPulseMode(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  time: number
) {
  const pulsePhase = (Math.sin(time * 1.2) + 1) / 2;
  const intensity = 0.2 + pulsePhase * 0.6;

  // Multiple concentric boundary rings expanding/contracting
  const ringCount = 3;
  for (let i = 0; i < ringCount; i++) {
    const ringPhase = (time * 0.8 + i * (Math.PI * 2 / ringCount)) % (Math.PI * 2);
    const ringPulse = (Math.sin(ringPhase) + 1) / 2;
    const ringRadius = r * (0.7 + ringPulse * 0.4);
    const ringAlpha = 0.05 + ringPulse * 0.15;

    drawArcGlow(ctx, cx, cy, ringRadius, startAngle, endAngle, [
      { offset: 0, color: `rgba(99, 102, 241, ${ringAlpha})` },
      { offset: 0.3, color: `rgba(129, 140, 248, ${ringAlpha * 1.2})` },
      { offset: 0.7, color: `rgba(129, 140, 248, ${ringAlpha * 1.2})` },
      { offset: 1, color: `rgba(99, 102, 241, ${ringAlpha})` },
    ], 2 + ringPulse * 4);
  }

  // Main arc with boundary glow
  drawArcGlow(ctx, cx, cy, r, startAngle, endAngle, [
    { offset: 0, color: `rgba(99, 102, 241, ${intensity * 0.4})` },
    { offset: 0.2, color: `rgba(129, 140, 248, ${intensity * 0.6})` },
    { offset: 0.5, color: `rgba(199, 210, 254, ${intensity * 0.8})` },
    { offset: 0.8, color: `rgba(129, 140, 248, ${intensity * 0.6})` },
    { offset: 1, color: `rgba(99, 102, 241, ${intensity * 0.4})` },
  ], 4 + pulsePhase * 6);

  // Boundary endpoints glow
  const endpointGlow = 0.3 + pulsePhase * 0.5;
  [startAngle, endAngle].forEach((angle) => {
    const ex = cx + Math.cos(angle) * r;
    const ey = cy + Math.sin(angle) * r;

    const gradient = ctx.createRadialGradient(ex, ey, 0, ex, ey, 40);
    gradient.addColorStop(0, `rgba(199, 210, 254, ${endpointGlow})`);
    gradient.addColorStop(0.5, `rgba(129, 140, 248, ${endpointGlow * 0.5})`);
    gradient.addColorStop(1, "rgba(99, 102, 241, 0)");

    ctx.fillStyle = gradient;
    ctx.fillRect(ex - 40, ey - 40, 80, 80);
  });
}

// ============ Orbit Mode: Chaotic bounded motion with collision ============
function drawOrbitMode(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  time: number
) {
  const arcLength = endAngle - startAngle;

  // Base ring
  drawArcGlow(ctx, cx, cy, r, startAngle, endAngle, [
    { offset: 0, color: "rgba(99, 102, 241, 0.04)" },
    { offset: 0.5, color: "rgba(129, 140, 248, 0.08)" },
    { offset: 1, color: "rgba(99, 102, 241, 0.04)" },
  ], 4);

  // Particles with chaotic bounded motion (Lissajous-like within arc)
  const particles = [
    { a: 1, b: 2, phase: 0, size: 1.0, color: "#c7d2fe", speed: 0.4 },
    { a: 2, b: 3, phase: Math.PI * 0.3, size: 0.8, color: "#818cf8", speed: 0.3 },
    { a: 3, b: 2, phase: Math.PI * 0.7, size: 0.6, color: "#a5b4fc", speed: 0.5 },
    { a: 1, b: 3, phase: Math.PI * 1.1, size: 0.7, color: "#6366f1", speed: 0.35 },
    { a: 2, b: 1, phase: Math.PI * 1.5, size: 0.5, color: "#c7d2fe", speed: 0.45 },
    { a: 3, b: 1, phase: Math.PI * 0.2, size: 0.4, color: "#818cf8", speed: 0.55 },
  ];

  particles.forEach((particle) => {
    // Lissajous curve bounded within arc
    const t = time * particle.speed + particle.phase;
    const x = Math.sin(particle.a * t);
    const y = Math.cos(particle.b * t);

    // Map to arc position with boundary reflection
    const arcPos = (x + 1) / 2; // 0 to 1
    const radialOffset = y * 0.15; // -0.15 to 0.15 (radial oscillation)

    const angle = startAngle + arcLength * arcPos;
    const currentRadius = r * (1 + radialOffset);

    const px = cx + Math.cos(angle) * currentRadius;
    const py = cy + Math.sin(angle) * currentRadius;

    const baseSize = 18 * particle.size;

    // Velocity-based glow intensity
    const dx = particle.a * Math.cos(particle.a * t);
    const dy = -particle.b * Math.sin(particle.b * t);
    const velocity = Math.sqrt(dx * dx + dy * dy);
    const intensity = 0.5 + Math.min(velocity * 0.15, 0.5);

    // Outer glow
    const outerGradient = ctx.createRadialGradient(px, py, 0, px, py, baseSize * 3);
    outerGradient.addColorStop(0, hexToRgba(particle.color, 0.5 * intensity));
    outerGradient.addColorStop(0.4, hexToRgba(particle.color, 0.2 * intensity));
    outerGradient.addColorStop(1, "rgba(99, 102, 241, 0)");

    ctx.fillStyle = outerGradient;
    ctx.fillRect(px - baseSize * 3, py - baseSize * 3, baseSize * 6, baseSize * 6);

    // Core
    const coreGradient = ctx.createRadialGradient(px, py, 0, px, py, baseSize * 0.6);
    coreGradient.addColorStop(0, `rgba(255, 255, 255, ${0.85 * intensity})`);
    coreGradient.addColorStop(1, hexToRgba(particle.color, 0));

    ctx.fillStyle = coreGradient;
    ctx.fillRect(px - baseSize * 0.6, py - baseSize * 0.6, baseSize * 1.2, baseSize * 1.2);

    // Chaotic trail
    const trailPoints = 8;
    for (let i = 1; i <= trailPoints; i++) {
      const trailT = t - i * 0.05;
      const tx = Math.sin(particle.a * trailT);
      const ty = Math.cos(particle.b * trailT);
      const trailArcPos = (tx + 1) / 2;
      const trailRadial = ty * 0.15;
      const trailAngle = startAngle + arcLength * trailArcPos;
      const trailRadius = r * (1 + trailRadial);
      const tpx = cx + Math.cos(trailAngle) * trailRadius;
      const tpy = cy + Math.sin(trailAngle) * trailRadius;

      const trailAlpha = (1 - i / trailPoints) * 0.15 * intensity;
      const trailSize = baseSize * 0.3 * (1 - i / trailPoints);

      ctx.beginPath();
      ctx.arc(tpx, tpy, trailSize, 0, Math.PI * 2);
      ctx.fillStyle = hexToRgba(particle.color, trailAlpha);
      ctx.fill();
    }
  });

  // Boundary collision sparks
  const sparkCount = 4;
  for (let i = 0; i < sparkCount; i++) {
    const sparkPhase = (time * 1.5 + i * (Math.PI * 2 / sparkCount)) % (Math.PI * 2);
    const sparkIntensity = Math.max(0, Math.sin(sparkPhase));

    if (sparkIntensity > 0.1) {
      [startAngle, endAngle].forEach((angle) => {
        const sx = cx + Math.cos(angle) * r;
        const sy = cy + Math.sin(angle) * r;

        const sparkGradient = ctx.createRadialGradient(sx, sy, 0, sx, sy, 25);
        sparkGradient.addColorStop(0, `rgba(255, 255, 255, ${sparkIntensity * 0.6})`);
        sparkGradient.addColorStop(0.5, `rgba(199, 210, 254, ${sparkIntensity * 0.3})`);
        sparkGradient.addColorStop(1, "rgba(99, 102, 241, 0)");

        ctx.fillStyle = sparkGradient;
        ctx.fillRect(sx - 25, sy - 25, 50, 50);
      });
    }
  }
}

// ============ Helper: Draw an arc with gradient glow ============
function drawArcGlow(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  colorStops: { offset: number; color: string }[],
  lineWidth: number
) {
  const steps = 120;
  const angleStep = (endAngle - startAngle) / steps;

  for (let i = 0; i < steps; i++) {
    const angle = startAngle + i * angleStep;
    const nextAngle = startAngle + (i + 1) * angleStep;
    const normalizedPos = i / steps;

    const color = interpolateColor(colorStops, normalizedPos);

    ctx.beginPath();
    ctx.arc(cx, cy, r, angle, nextAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.stroke();
  }
}

function interpolateColor(
  stops: { offset: number; color: string }[],
  position: number
): string {
  let lower = stops[0];
  let upper = stops[stops.length - 1];

  for (let i = 0; i < stops.length - 1; i++) {
    if (position >= stops[i].offset && position <= stops[i + 1].offset) {
      lower = stops[i];
      upper = stops[i + 1];
      break;
    }
  }

  if (lower.offset === upper.offset) return lower.color;

  const t = (position - lower.offset) / (upper.offset - lower.offset);

  const lowerRgba = parseRgba(lower.color);
  const upperRgba = parseRgba(upper.color);

  const r = Math.round(lowerRgba.r + (upperRgba.r - lowerRgba.r) * t);
  const g = Math.round(lowerRgba.g + (upperRgba.g - lowerRgba.g) * t);
  const b = Math.round(lowerRgba.b + (upperRgba.b - lowerRgba.b) * t);
  const a = lowerRgba.a + (upperRgba.a - lowerRgba.a) * t;

  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function parseRgba(rgba: string): { r: number; g: number; b: number; a: number } {
  const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
  if (match) {
    return {
      r: parseInt(match[1], 10),
      g: parseInt(match[2], 10),
      b: parseInt(match[3], 10),
      a: match[4] ? parseFloat(match[4]) : 1,
    };
  }
  return { r: 255, g: 255, b: 255, a: 1 };
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
