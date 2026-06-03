"use client";

import { useEffect, useRef } from "react";

interface WaveCanvasProps {
  className?: string;
}

export default function WaveCanvas({ className = "" }: WaveCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    function resizeCanvas() {
      canvas!.width = window.innerWidth || document.documentElement.clientWidth;
      canvas!.height = window.innerHeight || document.documentElement.clientHeight;
    }

    resizeCanvas();
    window.addEventListener("resize", resizeCanvas);
    setTimeout(resizeCanvas, 100);

    const opt = {
      density: 2.5,
      dotSize: 1.1,
      baseHeight: 140,
      verticalCount: 65,
      speed: 0.008,
    };

    let time = 0;

    function draw() {
      if (!ctx || !canvas) return;

      ctx.fillStyle = "#030305";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      time += opt.speed;

      const centerY = canvas.height * 0.5;

      for (let x = 0; x < canvas.width; x += opt.density) {
        // 三重波形叠加 - 制造不规律有机流动
        let wave1 = Math.sin(x * 0.002 + time);
        let wave2 = Math.sin(x * 0.005 - time * 0.7) * 0.4;
        let wave3 = Math.cos(x * 0.001 + time * 0.3) * 0.3;

        // 复合得到不规律主轨迹
        let baseY = (wave1 + wave2 + wave3) * opt.baseHeight + centerY;

        // 左侧宽、右侧自然收束
        let widthFade = 1 - (x / canvas.width);
        let currentVerticalCount = opt.verticalCount * (0.4 + widthFade * 0.8);

        for (let i = 0; i < currentVerticalCount; i++) {
          let offset = (i - currentVerticalCount / 2) * 4;
          let curY = baseY + offset;

          if (curY < 0 || curY > canvas.height) continue;

          let dist = Math.abs(offset);
          let currentMaxDist = (currentVerticalCount / 2) * 4;

          // 离散边缘概率
          let prob = Math.pow(1 - (dist / currentMaxDist), 2.0);

          if (Math.random() < prob) {
            // 基础透明度
            let alpha = (1 - (dist / currentMaxDist)) * 0.65;
            // 越往左侧越亮
            alpha *= (0.4 + widthFade * 0.6);
            // 微闪烁
            alpha *= (0.7 + Math.random() * 0.3);

            // 冷白蓝色调
            ctx.fillStyle = `rgba(235, 242, 255, ${alpha})`;

            let jitterX = (Math.random() - 0.5) * 1.8;
            let jitterY = (Math.random() - 0.5) * 1.8;

            ctx.fillRect(
              x + jitterX,
              curY + jitterY,
              opt.dotSize,
              opt.dotSize
            );
          }
        }
      }

      animationRef.current = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      window.removeEventListener("resize", resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={`absolute inset-0 w-full h-full pointer-events-none ${className}`}
      style={{ zIndex: 1 }}
    />
  );
}
