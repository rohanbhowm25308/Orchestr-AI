// Ambient starfield background — sparse stars slowly pulsing brightness.
// No connecting lines, just quiet, minimal twinkle.
(function () {
  const canvas = document.getElementById("particle-field");
  const ctx = canvas.getContext("2d");
  let width, height, stars;
  const COUNT_DIVISOR = 9000; // lower = more stars

  function resize() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    const count = Math.min(220, Math.floor((width * height) / COUNT_DIVISOR));
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: Math.random() * 1.3 + 0.4,
      phase: Math.random() * Math.PI * 2,
      speed: 0.008 + Math.random() * 0.014,
    }));
  }

  let t = 0;

  function step() {
    t += 1;
    ctx.clearRect(0, 0, width, height);

    for (const s of stars) {
      const opacity = 0.2 + 0.8 * Math.abs(Math.sin(t * s.speed + s.phase));
      const grad = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 4);
      grad.addColorStop(0, `rgba(200,220,255,${0.35 * opacity})`);
      grad.addColorStop(1, "rgba(200,220,255,0)");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r * 4, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(225,238,255,${opacity})`;
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
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
    // Draw a single static frame at mid-brightness for users who prefer
    // reduced motion, instead of a looping animation.
    ctx.clearRect(0, 0, width, height);
    for (const s of stars) {
      ctx.fillStyle = "rgba(225,238,255,0.6)";
      ctx.beginPath();
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
})();