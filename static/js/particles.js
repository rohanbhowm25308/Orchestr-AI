// Ambient particle-network background — glowing nodes drifting slowly and
// connecting to nearby neighbors, echoing OrchestrAI's agent-network theme.
(function () {
  const canvas = document.getElementById("particle-field");
  const ctx = canvas.getContext("2d");
  let width, height, particles;
  const LINK_DIST = 150;
  const COUNT_DIVISOR = 14000; // lower = more particles

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    const count = Math.min(90, Math.floor((width * height) / COUNT_DIVISOR));
    particles = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
      r: Math.random() * 1.6 + 0.6,
      glow: Math.random() * 0.5 + 0.5,
    }));
  }

  function step() {
    ctx.clearRect(0, 0, width, height);

    for (const p of particles) {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > width) p.vx *= -1;
      if (p.y < 0 || p.y > height) p.vy *= -1;
    }

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const a = particles[i], b = particles[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < LINK_DIST) {
          const alpha = (1 - dist / LINK_DIST) * 0.16;
          ctx.strokeStyle = `rgba(90,150,255,${alpha})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    for (const p of particles) {
      const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 5);
      grad.addColorStop(0, `rgba(120,190,255,${0.55 * p.glow})`);
      grad.addColorStop(1, "rgba(120,190,255,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r * 5, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(220,235,255,${0.85 * p.glow})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(step);
  }

  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  window.addEventListener("resize", resize);
  resize();

  if (!prefersReducedMotion) {
    requestAnimationFrame(step);
  } else {
    // Draw a single static frame for users who prefer reduced motion.
    step_once();
  }

  function step_once() {
    ctx.clearRect(0, 0, width, height);
    for (const p of particles) {
      ctx.fillStyle = `rgba(220,235,255,${0.6 * p.glow})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
})();
