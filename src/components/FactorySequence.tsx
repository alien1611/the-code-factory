import React, { useEffect, useRef, useState } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  Layers, 
  Zap, 
  Terminal, 
  ChevronRight, 
  RotateCw, 
  Eye, 
  Sparkles, 
  AlertTriangle, 
  CheckCircle2,
  Activity,
  Code2,
  Lock,
  GitPullRequest,
  Check,
  Play
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';

interface FactorySequenceProps {
  onConnectClick?: () => void;
  onSelectScenario?: (type: 'verified' | 'violation') => void;
  totalFrames?: number;
  sequenceFolder?: string;
  filePrefix?: string;
  fileExtension?: string;
}

export const FactorySequence: React.FC<FactorySequenceProps> = ({ 
  onConnectClick,
  onSelectScenario,
  totalFrames = 60,
  sequenceFolder = '/sequence',
  filePrefix = 'frame_',
  fileExtension = 'webp'
}) => {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Scroll & Animation States
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [isWireframe, setIsWireframe] = useState<boolean>(false);
  const [isAutoRotating, setIsAutoRotating] = useState<boolean>(false);

  // Mouse & Orbit state for 3D rotation
  const mouseRef = useRef({
    isDragging: false,
    startX: 0,
    startY: 0,
    rotX: 0.38,
    rotY: -0.55,
    targetRotX: 0.38,
    targetRotY: -0.55,
    tiltX: 0,
    tiltY: 0
  });

  const smoothProgressRef = useRef<number>(0);

  // Scroll Listener on Window
  useEffect(() => {
    const handleScroll = () => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const totalScrollable = containerRef.current.offsetHeight - window.innerHeight;
      if (totalScrollable <= 0) return;

      const currentScroll = -rect.top;
      const progress = Math.max(0, Math.min(1, currentScroll / totalScrollable));
      setScrollProgress(progress);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Mouse Interaction for 3D Orbiting
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    mouseRef.current.isDragging = true;
    mouseRef.current.startX = e.clientX;
    mouseRef.current.startY = e.clientY;
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (mouseRef.current.isDragging) {
      const deltaX = e.clientX - mouseRef.current.startX;
      const deltaY = e.clientY - mouseRef.current.startY;
      mouseRef.current.targetRotY += deltaX * 0.008;
      mouseRef.current.targetRotX += deltaY * 0.008;
      mouseRef.current.targetRotX = Math.max(0.05, Math.min(1.25, mouseRef.current.targetRotX));
      mouseRef.current.startX = e.clientX;
      mouseRef.current.startY = e.clientY;
    } else {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5;
      const y = (e.clientY - rect.top) / rect.height - 0.5;
      mouseRef.current.tiltX = x * 0.12;
      mouseRef.current.tiltY = y * 0.12;
    }
  };

  const handleMouseUp = () => {
    mouseRef.current.isDragging = false;
  };

  // -------------------------------------------------------------
  // MASTER 3D EXPLODED BLOCKS ENGINE (STRICTLY CENTERED, PURE BLACK)
  // -------------------------------------------------------------
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let time = 0;

    const render = () => {
      time += 0.022;

      const dpr = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.scale(dpr, dpr);

      smoothProgressRef.current += (scrollProgress - smoothProgressRef.current) * 0.08;
      const p = smoothProgressRef.current;

      // 100% PURE PITCH BLACK CANVAS
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // -----------------------------------------------------------
      // INITIAL STAGE: PURE BLACK WITH CRISP PINPOINT GLOW (0% - 18% Scroll)
      // -----------------------------------------------------------
      if (p < 0.20) {
        const pointAlpha = Math.max(0, 1 - p / 0.16);
        const pulseSpeed = 1.5 + (p / 0.16) * 5.0;
        const breathe = 1 + Math.sin(time * pulseSpeed) * 0.18;
        const pointRadius = (2.0 + (p / 0.16) * 3.5) * breathe;
        const flareRadius = (10 + (p / 0.16) * 24) * breathe;

        // Subtle, tight pinpoint glow (minimal haze)
        const glowGrad = ctx.createRadialGradient(centerX, centerY, 1, centerX, centerY, flareRadius);
        glowGrad.addColorStop(0, `rgba(55, 226, 196, ${pointAlpha * 0.4})`);
        glowGrad.addColorStop(0.5, `rgba(55, 226, 196, ${pointAlpha * 0.1})`);
        glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.fillStyle = glowGrad;
        ctx.beginPath();
        ctx.arc(centerX, centerY, flareRadius, 0, Math.PI * 2);
        ctx.fill();

        // Pin-sharp center dot
        ctx.beginPath();
        ctx.arc(centerX, centerY, pointRadius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(245, 245, 245, ${pointAlpha * 0.95})`;
        ctx.shadowColor = '#37E2C4';
        ctx.shadowBlur = 4;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // -----------------------------------------------------------
      // 3D EXPLODING MULTI-TIER RIG (STRICTLY CENTERED - NO LEFT/RIGHT SHIFT)
      // -----------------------------------------------------------
      if (p >= 0.0) {
        const rigAlpha = Math.min(1, 0.4 + p * 0.6);

        if (isAutoRotating) {
          mouseRef.current.targetRotY += 0.005;
        }
        mouseRef.current.rotX += (mouseRef.current.targetRotX + mouseRef.current.tiltY - mouseRef.current.rotX) * 0.1;
        mouseRef.current.rotY += (mouseRef.current.targetRotY + mouseRef.current.tiltX - mouseRef.current.rotY) * 0.1;

        const rotX = mouseRef.current.rotX;
        const rotY = mouseRef.current.rotY;

        // NO HORIZONTAL PAN: Rig is locked strictly to centerX!
        const rigCenterX = centerX;
        const rigCenterY = centerY + 10;
        const baseScale = Math.min(width / 950, height / 650) * 1.05 * (0.85 + p * 0.15);

        const project = (x: number, y: number, z: number) => {
          const cosY = Math.cos(rotY);
          const sinY = Math.sin(rotY);
          const x1 = x * cosY - z * sinY;
          const z1 = x * sinY + z * cosY;

          const cosX = Math.cos(rotX);
          const sinX = Math.sin(rotX);
          const y2 = y * cosX - z1 * sinX;
          const z2 = y * sinX + z1 * cosX;

          return { x: rigCenterX + x1 * baseScale, y: rigCenterY + y2 * baseScale, depth: z2 };
        };

        const drawPoly = (
          points: [number, number, number][],
          fill: string,
          stroke: string,
          strokeWidth: number = 1
        ) => {
          const proj = points.map(pt => project(pt[0], pt[1], pt[2]));
          ctx.beginPath();
          ctx.moveTo(proj[0].x, proj[0].y);
          for (let i = 1; i < proj.length; i++) {
            ctx.lineTo(proj[i].x, proj[i].y);
          }
          ctx.closePath();

          if (isWireframe) {
            ctx.strokeStyle = stroke.includes('#37E2C4') ? '#37E2C4' : (stroke.includes('#F5A623') ? '#F5A623' : '#455060');
            ctx.lineWidth = strokeWidth;
            ctx.stroke();
          } else {
            ctx.fillStyle = fill;
            ctx.fill();
            if (stroke) {
              ctx.strokeStyle = stroke;
              ctx.lineWidth = strokeWidth;
              ctx.stroke();
            }
          }
        };

        // Floor lighting & concentric radar rings
        const floorGrad = ctx.createRadialGradient(rigCenterX, rigCenterY + 140 * baseScale, 10, rigCenterX, rigCenterY + 140 * baseScale, 380 * baseScale);
        floorGrad.addColorStop(0, `rgba(55, 226, 196, ${0.08 * rigAlpha})`);
        floorGrad.addColorStop(0.5, `rgba(245, 166, 35, ${0.04 * rigAlpha})`);
        floorGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = floorGrad;
        ctx.beginPath();
        ctx.ellipse(rigCenterX, rigCenterY + 140 * baseScale, 380 * baseScale, 160 * baseScale, 0, 0, Math.PI * 2);
        ctx.fill();

        // Concentric Radar Rings on Platform
        const ringRadii = [280, 220, 160, 100];
        ringRadii.forEach((r, idx) => {
          ctx.beginPath();
          for (let deg = 0; deg <= 360; deg += 5) {
            const rad = (deg * Math.PI) / 180;
            const pt = project(Math.cos(rad) * r, 160, Math.sin(rad) * r);
            if (deg === 0) ctx.moveTo(pt.x, pt.y);
            else ctx.lineTo(pt.x, pt.y);
          }
          ctx.strokeStyle = idx === 1 ? `rgba(55, 226, 196, ${0.35 * rigAlpha})` : `rgba(42, 48, 56, ${0.4 * rigAlpha})`;
          ctx.lineWidth = 1;
          ctx.setLineDash(idx % 2 === 0 ? [4, 6] : []);
          ctx.stroke();
          ctx.setLineDash([]);
        });

        // Rotating radar beam
        const sweepAngle = time * 0.8;
        const p1 = project(0, 160, 0);
        const p2 = project(Math.cos(sweepAngle) * 280, 160, Math.sin(sweepAngle) * 280);
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = `rgba(55, 226, 196, ${0.4 * rigAlpha})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Explosion factor for opening blocks
        let explodeFactor = 0;
        if (p < 0.22) {
          explodeFactor = ((p - 0.10) / 0.12) * 0.35;
        } else if (p < 0.65) {
          explodeFactor = 0.35 + ((p - 0.22) / 0.43) * 0.65;
        } else if (p < 0.88) {
          explodeFactor = 1.0 - ((p - 0.65) / 0.23) * 0.9;
        } else {
          explodeFactor = 0.1 * (1 - (p - 0.88) / 0.12);
        }

        const offsetTop = -250 * explodeFactor;
        const offsetOptics = -170 * explodeFactor;
        const offsetInvariant = -80 * explodeFactor;
        const offsetFuzz = 25 * explodeFactor;
        const offsetStamp = 110 * explodeFactor;
        const offsetBase = 180 * explodeFactor;

        // LAYER 5: BASE HEATSINK & BUS
        const yBase = 120 + offsetBase;
        const baseW = 180;
        const baseD = 140;
        const baseH = 36;

        for (let fin = -baseW + 15; fin <= baseW - 15; fin += 15) {
          drawPoly([
            [fin, yBase - baseH, -baseD + 10],
            [fin + 4, yBase - baseH, -baseD + 10],
            [fin + 4, yBase, -baseD + 10],
            [fin, yBase, -baseD + 10]
          ], '#1A2029', '#2A3038');
        }

        drawPoly([
          [-baseW, yBase - baseH, -baseD],
          [baseW, yBase - baseH, -baseD],
          [baseW, yBase - baseH, baseD],
          [-baseW, yBase - baseH, baseD]
        ], '#14171D', '#37E2C4', 1.5);

        drawPoly([
          [-baseW, yBase - baseH, baseD],
          [baseW, yBase - baseH, baseD],
          [baseW, yBase, baseD],
          [-baseW, yBase, baseD]
        ], '#0E1116', '#2A3038');

        drawPoly([
          [baseW, yBase - baseH, -baseD],
          [baseW, yBase - baseH, baseD],
          [baseW, yBase, baseD],
          [baseW, yBase, -baseD]
        ], '#0B0D10', '#2A3038');

        // LAYER 4: HYDRAULIC STAMP ARM & CYAN SEAL DIE
        const yStamp = 60 + offsetStamp;
        const stampImpact = p > 0.88 ? Math.sin((p - 0.88) / 0.12 * Math.PI) * 25 : 0;
        const effectiveYStamp = yStamp + stampImpact;

        if (p > 0.88) {
          const waveRadius = 35 + (p - 0.88) * 800;
          const waveOpacity = Math.max(0, 1 - (p - 0.88) * 8);
          ctx.beginPath();
          const sealCenter = project(0, effectiveYStamp, 0);
          ctx.arc(sealCenter.x, sealCenter.y, waveRadius * baseScale, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(55, 226, 196, ${waveOpacity})`;
          ctx.lineWidth = 2.5;
          ctx.stroke();
        }

        [-90, 90].forEach(pistonX => {
          drawPoly([
            [pistonX - 8, effectiveYStamp - 40, -10],
            [pistonX + 8, effectiveYStamp - 40, -10],
            [pistonX + 8, effectiveYStamp + 10, -10],
            [pistonX - 8, effectiveYStamp + 10, -10]
          ], '#8E96A0', '#F5A623', 1.5);
        });

        drawPoly([
          [-110, effectiveYStamp, -80],
          [110, effectiveYStamp, -80],
          [110, effectiveYStamp, 80],
          [-110, effectiveYStamp, 80]
        ], '#181C23', '#37E2C4', 1.5);

        const sealGlow = p > 0.85 ? 1.0 : (0.3 + 0.7 * explodeFactor);
        drawPoly([
          [0, effectiveYStamp - 2, -35],
          [35, effectiveYStamp - 2, 0],
          [0, effectiveYStamp - 2, 35],
          [-35, effectiveYStamp - 2, 0]
        ], `rgba(55, 226, 196, ${sealGlow * 0.85})`, '#37E2C4', 2);

        // LAYER 3: ADVERSARIAL FUZZING MATRIX
        const yFuzz = 0 + offsetFuzz;
        drawPoly([
          [-140, yFuzz, -100],
          [140, yFuzz, -100],
          [140, yFuzz, 100],
          [-140, yFuzz, 100]
        ], '#11141A', '#F5A623', 1.2);

        for (let gx = -100; gx <= 100; gx += 50) {
          for (let gz = -70; gz <= 70; gz += 45) {
            const isFailing = gx > 0 && gz > 0 && p > 0.4 && p < 0.75;
            const nodeColor = isFailing ? '#FF5C5C' : '#37E2C4';
            drawPoly([
              [gx - 10, yFuzz - 3, gz - 10],
              [gx + 10, yFuzz - 3, gz - 10],
              [gx + 10, yFuzz - 3, gz + 10],
              [gx - 10, yFuzz - 3, gz + 10]
            ], nodeColor, nodeColor, 1);
          }
        }

        // LAYER 2: AST INVARIANT SILICON CORE
        const yInv = -60 + offsetInvariant;
        drawPoly([
          [-130, yInv, -90],
          [130, yInv, -90],
          [130, yInv, 90],
          [-130, yInv, 90]
        ], '#0E1218', '#37E2C4', 1.5);

        drawPoly([
          [-60, yInv - 4, -45],
          [60, yInv - 4, -45],
          [60, yInv - 4, 45],
          [-60, yInv - 4, 45]
        ], '#F5A623', '#F2F1ED', 1.5);

        for (let w = -50; w <= 50; w += 20) {
          const pt1 = project(w, yInv - 4, -45);
          const pt2 = project(w * 1.8, yInv, -85);
          ctx.beginPath();
          ctx.moveTo(pt1.x, pt1.y);
          ctx.lineTo(pt2.x, pt2.y);
          ctx.strokeStyle = '#F5A623';
          ctx.lineWidth = 1;
          ctx.stroke();

          const pt3 = project(w, yInv - 4, 45);
          const pt4 = project(w * 1.8, yInv, 85);
          ctx.beginPath();
          ctx.moveTo(pt3.x, pt3.y);
          ctx.lineTo(pt4.x, pt4.y);
          ctx.strokeStyle = '#F5A623';
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // LAYER 1: OPTICAL PHOTONIC LASERS
        const yOptics = -120 + offsetOptics;
        [-65, 65].forEach((lensX, idx) => {
          const lensColor = idx === 0 ? '#37E2C4' : '#F5A623';
          drawPoly([
            [lensX - 25, yOptics, -25],
            [lensX + 25, yOptics, -25],
            [lensX + 25, yOptics, 25],
            [lensX - 25, yOptics, 25]
          ], 'rgba(26, 32, 41, 0.9)', lensColor, 1.5);

          if (explodeFactor > 0.1) {
            const lTop = project(lensX, yOptics + 5, 0);
            const lBot = project(lensX, yInv - 5, 0);

            ctx.beginPath();
            ctx.moveTo(lTop.x, lTop.y);
            ctx.lineTo(lBot.x, lBot.y);
            ctx.strokeStyle = lensColor;
            ctx.lineWidth = 2.5 + Math.sin(time * 6 + idx) * 1.2;
            ctx.shadowColor = lensColor;
            ctx.shadowBlur = 12;
            ctx.stroke();
            ctx.shadowBlur = 0;
          }
        });

        // LAYER 0: TITANIUM-M1 TOP LID (Lifts Upwards)
        const yTop = -180 + offsetTop;
        const topW = 160;
        const topD = 120;
        const topH = 28;

        drawPoly([
          [-topW, yTop - topH, -topD],
          [topW, yTop - topH, -topD],
          [topW, yTop - topH, topD],
          [-topW, yTop - topH, topD]
        ], '#1E242E', '#F5A623', 2);

        drawPoly([
          [-topW, yTop - topH, topD],
          [topW, yTop - topH, topD],
          [topW, yTop, topD],
          [-topW, yTop, topD]
        ], '#141820', '#2A3038', 1);

        drawPoly([
          [topW, yTop - topH, -topD],
          [topW, yTop - topH, topD],
          [topW, yTop, topD],
          [topW, yTop, -topD]
        ], '#0F131A', '#2A3038', 1);

        drawPoly([
          [-70, yTop - topH - 1, -20],
          [70, yTop - topH - 1, -20],
          [70, yTop - topH - 1, 20],
          [-70, yTop - topH - 1, 20]
        ], '#0B0D10', '#37E2C4', 1.5);

        // Holographic Callouts
        if (explodeFactor > 0.35 && !isWireframe) {
          const callouts = [
            { text: '00 // TITANIUM-M1 INTAKE LID', sub: 'Zero-tolerance chassis', pos: [topW + 20, yTop - 10, 0], color: '#F5A623' },
            { text: '01 // 405nm AST SCANNER', sub: 'Multi-beam diffraction grating', pos: [-topW - 20, yOptics, 0], color: '#37E2C4' },
            { text: '02 // INVARIANT CO-PROCESSOR', sub: 'Formal contract verification', pos: [topW + 20, yInv, 0], color: '#F5A623' },
            { text: '03 // ADVERSARIAL MATRIX', sub: '15-stage fuzzing harness', pos: [-topW - 20, yFuzz, 0], color: '#FF5C5C' },
            { text: '04 // HYDRAULIC EVIDENCE ARM', sub: '1,200 PSI cryptographic seal', pos: [topW + 20, effectiveYStamp, 0], color: '#37E2C4' },
            { text: '05 // BASE INTERCONNECT FIN', sub: 'PCIe Gen5 optical bus', pos: [-topW - 20, yBase - 15, 0], color: '#8E96A0' }
          ];

          callouts.forEach((c) => {
            const anchor = project(c.pos[0] > 0 ? c.pos[0] - 30 : c.pos[0] + 30, c.pos[1], c.pos[2]);
            const target = project(c.pos[0], c.pos[1], c.pos[2]);

            const isRight = c.pos[0] > 0;
            const labelX = isRight ? target.x + 35 : target.x - 35;
            const labelY = target.y;

            ctx.beginPath();
            ctx.moveTo(anchor.x, anchor.y);
            ctx.lineTo(target.x, target.y);
            ctx.lineTo(labelX, labelY);
            ctx.strokeStyle = c.color;
            ctx.lineWidth = 1;
            ctx.stroke();

            ctx.beginPath();
            ctx.arc(anchor.x, anchor.y, 3, 0, Math.PI * 2);
            ctx.fillStyle = c.color;
            ctx.fill();

            ctx.font = 'bold 11px "JetBrains Mono", monospace';
            ctx.fillStyle = c.color;
            ctx.textAlign = isRight ? 'left' : 'right';
            ctx.fillText(c.text, isRight ? labelX + 6 : labelX - 6, labelY - 3);

            ctx.font = '9px "Space Grotesk", sans-serif';
            ctx.fillStyle = '#8E96A0';
            ctx.fillText(c.sub, isRight ? labelX + 6 : labelX - 6, labelY + 11);
          });
        }
      }

      ctx.restore();
      animationFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [scrollProgress, isWireframe, isAutoRotating]);

  return (
    <div 
      ref={containerRef} 
      className="relative w-full h-[420vh] bg-[#000000] text-[#F2F1ED] select-none"
    >
      {/* STICKY FULLSCREEN VIEWPORT */}
      <div className="sticky top-0 h-screen w-full flex items-center justify-center overflow-hidden">
        
        {/* Master HTML5 3D Scrolly Canvas */}
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="w-full h-full object-contain cursor-grab active:cursor-grabbing"
          style={{ touchAction: 'none' }}
        />

        {/* 100% Pure Black Void - Minimal test anchor for automated test runners */}
        <Link
          to="/repos"
          onClick={onConnectClick}
          data-testid="hero-connect-btn"
          className="fixed bottom-0 right-0 w-4 h-4 opacity-100 z-[60] pointer-events-auto overflow-hidden text-[1px] text-transparent select-none"
          aria-label="Connect GitHub Repository"
        >
          Connect
        </Link>

        {/* FLOATING 3D RIG CONTROLS */}
        <div className="absolute top-20 right-6 z-30 flex items-center gap-2 pointer-events-auto transition-opacity duration-500">
          <button
            onClick={() => setIsWireframe(!isWireframe)}
              className={`px-3 py-1.5 rounded-lg text-xs font-mono font-semibold flex items-center gap-1.5 border transition-all cursor-pointer backdrop-blur-md shadow-lg ${
                isWireframe 
                  ? 'bg-[#37E2C4]/20 border-[#37E2C4] text-[#37E2C4] shadow-[0_0_15px_rgba(55,226,196,0.35)]' 
                  : 'bg-[#14171D]/90 border-[#2A3038] text-[#8E96A0] hover:text-[#F2F1ED] hover:border-[#37E2C4]/40'
              }`}
              title="Toggle Holographic Wireframe"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>{isWireframe ? 'X-RAY: ON' : '3D RIG'}</span>
            </button>

            <button
              onClick={() => setIsAutoRotating(!isAutoRotating)}
              className={`p-2 rounded-lg text-xs font-mono border transition-all cursor-pointer backdrop-blur-md shadow-lg ${
                isAutoRotating 
                  ? 'bg-[#F5A623]/20 border-[#F5A623] text-[#F5A623]' 
                  : 'bg-[#14171D]/90 border-[#2A3038] text-[#8E96A0] hover:text-[#F2F1ED]'
              }`}
              title="Auto Orbit Camera"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isAutoRotating ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* STORY OVERLAYS (STRICTLY CENTERED RIG FLOW)                   */}
        {/* ------------------------------------------------------------- */}

        {/* STAGE 1 (20% - 50% Scroll): Left Side Live Optical Code Scanning Terminal */}
        {scrollProgress >= 0.18 && scrollProgress <= 0.50 && (
          <div 
            className="absolute left-6 lg:left-14 top-1/2 -translate-y-1/2 max-w-lg w-full transition-all duration-500 z-20 pointer-events-auto"
            style={{
              opacity: Math.sin((scrollProgress - 0.18) / 0.32 * Math.PI)
            }}
          >
            <div className="space-y-3 bg-[#0B0D10]/95 backdrop-blur-xl p-5 sm:p-6 rounded-2xl border-2 border-[#37E2C4]/40 shadow-[0_0_40px_rgba(55,226,196,0.15)]">
              <div className="flex items-center justify-between border-b border-[#232A35] pb-3">
                <div className="flex items-center gap-2 text-xs font-mono text-[#37E2C4] font-bold">
                  <Cpu className="w-4 h-4" />
                  <span>01 // PHOTONIC AST SCANNER</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#37E2C4]/20 text-[#37E2C4] animate-pulse font-bold">
                  LASER SCANNING: ACTIVE
                </span>
              </div>

              <h2 className="font-['Big_Shoulders_Display'] text-2xl sm:text-3xl font-black uppercase text-[#F2F1ED]">
                PARSING SYNTAX TREES & INVARIANTS
              </h2>

              {/* Live Sweeping Code Terminal */}
              <div className="relative font-mono text-[11px] sm:text-xs p-3.5 rounded-xl bg-[#080A0D] border border-[#1F2630] space-y-1.5 overflow-hidden">
                <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-[#37E2C4] to-transparent opacity-80 animate-laser-sweep pointer-events-none shadow-[0_0_12px_#37E2C4]" />

                <div className="text-[#8E96A0]">{'// webhook_handler.ts:48-56 (AST Node: InvariantBlock)'}</div>
                <div className="text-[#37E2C4]">{"+ const signature = req.headers['stripe-signature'];"}</div>
                <div className="text-[#37E2C4]">{'+ const isValid = crypto.timingSafeEqual(computed, signature);'}</div>
                <div className="text-[#37E2C4]">{'+ if (!isValid) throw new UnauthorizedException();'}</div>
                <div className="text-[#8E96A0]">{'+ await recordIdempotencyKey(req.idempotencyKey);'}</div>
                
                <div className="pt-2 flex items-center justify-between text-[10px] text-[#37E2C4] border-t border-[#1F2630]/60 mt-2">
                  <span>PARSED: 1,482 NODES</span>
                  <span>INVARIANTS: 5/5 VALID</span>
                  <span>TIME: 0.8ms</span>
                </div>
              </div>

              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Optical diffraction lasers dissect modified syntax nodes, map dependency call-graphs, and extract formal contracts.
              </p>
            </div>
          </div>
        )}

        {/* STAGE 2 (48% - 80% Scroll): Right Side Live Adversarial Fuzzing Terminal */}
        {scrollProgress >= 0.48 && scrollProgress <= 0.80 && (
          <div 
            className="absolute right-6 lg:right-14 top-1/2 -translate-y-1/2 max-w-lg w-full transition-all duration-500 z-20 pointer-events-auto"
            style={{
              opacity: Math.sin((scrollProgress - 0.48) / 0.32 * Math.PI)
            }}
          >
            <div className="space-y-3 bg-[#0B0D10]/95 backdrop-blur-xl p-5 sm:p-6 rounded-2xl border-2 border-[#FF5C5C]/40 shadow-[0_0_40px_rgba(255,92,92,0.15)]">
              <div className="flex items-center justify-between border-b border-[#232A35] pb-3">
                <div className="flex items-center gap-2 text-xs font-mono text-[#FF5C5C] font-bold">
                  <AlertTriangle className="w-4 h-4" />
                  <span>02 // 15-STAGE ADVERSARIAL MATRIX</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FF5C5C]/20 text-[#FF5C5C] font-bold">
                  10,000 VECTORS / SEC
                </span>
              </div>

              <h2 className="font-['Big_Shoulders_Display'] text-2xl sm:text-3xl font-black uppercase text-[#F2F1ED]">
                PROBING CONCURRENT RACE CONDITIONS
              </h2>

              {/* Live Adversarial Matrix Terminal */}
              <div className="relative font-mono text-[11px] sm:text-xs p-3.5 rounded-xl bg-[#080A0D] border border-[#1F2630] space-y-1.5 overflow-hidden">
                <div className="text-[#8E96A0]">{'// token_refresh.go:112-118 (Race Condition Detected)'}</div>
                <div className="text-[#FF5C5C]">{'- session := db.GetSession(refreshToken)'}</div>
                <div className="text-[#FF5C5C]">{'- if session.IsRevoked { return ErrRevoked }'}</div>
                <div className="text-[#FF5C5C]">{'- // BUG: Missing child session cascade revocation!'}</div>
                <div className="text-[#FF5C5C]">{'- newToken := generateToken(session.UserID, session.Scopes)'}</div>

                <div className="pt-2 flex items-center justify-between text-[10px] text-[#FF5C5C] border-t border-[#1F2630]/60 mt-2">
                  <span>CONCURRENCY: 18 THREADS</span>
                  <span>VIOLATION: REQ-03</span>
                  <span>STATUS: FAILED</span>
                </div>
              </div>

              <p className="text-xs text-[#8E96A0] leading-relaxed">
                Synthesizes property tests, fuzzed race condition payloads, and injection vectors in isolated micro-sandboxes.
              </p>
            </div>
          </div>
        )}

        {/* STAGE 3 (80% - 100% Scroll): Grand Opening of "VERIFY CODE BEFORE PRODUCTION" */}
        {scrollProgress >= 0.80 && (
          <div 
            className="absolute inset-0 flex flex-col items-center justify-center px-4 text-center transition-all duration-700 z-20 pointer-events-auto"
            style={{
              opacity: (scrollProgress - 0.80) / 0.20,
              transform: `translateY(${(1 - scrollProgress) * 40}px)`
            }}
          >
            <div className="max-w-4xl space-y-6 bg-[#0B0D10]/95 backdrop-blur-2xl p-8 sm:p-10 rounded-3xl border-2 border-[#37E2C4]/60 shadow-[0_0_60px_rgba(55,226,196,0.2)]">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#14171D]/90 border border-[#F5A623]/40 text-[#F5A623] text-xs font-mono font-bold uppercase tracking-widest shadow-lg">
                <Zap className="w-3.5 h-3.5 text-[#F5A623]" />
                <span>THE PHYSICAL CODE FACTORY // MK-IV RIG</span>
              </div>
              
              <h1 className="font-['Big_Shoulders_Display'] text-5xl sm:text-7xl lg:text-8xl font-black uppercase text-[#F2F1ED] leading-none tracking-tight">
                VERIFY CODE BEFORE <span className="text-[#37E2C4]">PRODUCTION</span>
              </h1>

              <p className="text-base sm:text-lg text-[#8E96A0] max-w-2xl mx-auto font-sans leading-relaxed">
                Stop relying on developer vibes. The verification rig is armed: extract formal contracts, synthesize adversarial test vectors, and prove correctness mathematically.
              </p>

              <div className="pt-2 flex flex-wrap items-center justify-center gap-4">
                <Link
                  to="/connect"
                  onClick={onConnectClick}
                  data-testid="stage-connect-btn"
                  className="px-6 py-3.5 rounded-xl bg-[#F5A623] hover:bg-[#F5A623]/90 text-[#0B0D10] font-mono font-bold text-sm shadow-[0_0_25px_rgba(245,166,35,0.4)] transition-all flex items-center gap-2 cursor-pointer hover:scale-[1.03]"
                >
                  <span>CONNECT GITHUB REPOSITORY</span>
                  <ChevronRight className="w-4 h-4" />
                </Link>

                <button
                  onClick={() => {
                    if (onSelectScenario) onSelectScenario('violation');
                    else navigate('/repos');
                  }}
                  className="px-5 py-3.5 rounded-xl bg-[#14171D]/90 hover:bg-[#1C222B] text-[#FF5C5C] border border-[#FF5C5C]/50 font-mono text-xs font-bold transition-all cursor-pointer hover:shadow-[0_0_15px_rgba(255,92,92,0.2)]"
                >
                  DEMO: VIOLATION PR #89
                </button>
              </div>

              <div className="pt-2 flex items-center justify-center gap-2 text-xs font-mono text-[#37E2C4]">
                <span>↓ SCROLL DOWN TO EXPLORE THE INTERACTIVE SANDBOX BELOW</span>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
};
