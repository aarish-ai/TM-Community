/**
 * Truth Mirror - Landing Page Terminal & Cache Dropdown Logic
 */
document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("landingSearchInput");
  const searchBar = document.getElementById("landingSearchBar");
  const searchForm = document.getElementById("landingSearchForm");
  const analyzeBtn = document.getElementById("landingAnalyzeBtn");
  const cacheDropdown = document.getElementById("cacheDropdown");
  const cacheList = document.getElementById("cacheList");
  const guestLimitNotice = document.getElementById("guestLimitNotice");
  const dismissNoticeBtn = document.getElementById("dismissNoticeBtn");

  const signinBtn = document.querySelector(".nav-signin-btn");
  if (signinBtn) {
      const token = sessionStorage.getItem("tm_token") || localStorage.getItem("token");
      if (token) {
          signinBtn.textContent = "Sign Out";
          signinBtn.href = "#";
          signinBtn.addEventListener("click", (e) => {
              if (signinBtn.textContent === "Sign Out") {
                  e.preventDefault();
                  sessionStorage.removeItem("tm_token");
                  localStorage.removeItem("token");
                  window.location.reload();
              }
          });
          
          fetch("/api/validate", { headers: { "Authorization": "Bearer " + token } })
              .then(res => {
                  if (!res.ok) {
                      sessionStorage.removeItem("tm_token");
                      localStorage.removeItem("token");
                      signinBtn.textContent = "Sign In";
                      signinBtn.href = "/static/login.html";
                  }
              }).catch(console.error);
      }
  }

  let CACHED_CLAIMS = [];
  fetch("/api/cached-claims")
    .then(res => res.json())
    .then(data => {
      if (data.claims && Array.isArray(data.claims)) {
        CACHED_CLAIMS = data.claims;
        if (cacheDropdown && cacheDropdown.style.display === "block") {
          renderCacheList(searchInput ? searchInput.value : "");
        }
      }
    })
    .catch(err => console.error("Failed to load cached claims:", err));

  function renderCacheList(filterQuery = "") {
    if (!cacheList) return;
    cacheList.innerHTML = "";
    
    const query = filterQuery.toLowerCase().trim();
    const filtered = query 
      ? CACHED_CLAIMS.filter(item => (item.claim && item.claim.toLowerCase().includes(query)) || (item.category && item.category.toLowerCase().includes(query)))
      : CACHED_CLAIMS;

    if (filtered.length === 0) {
      const emptyLi = document.createElement("li");
      emptyLi.className = "cache-item-empty";
      emptyLi.innerHTML = `<span>No exact cache match. Press <strong>Enter</strong> to run custom claim analysis.</span>`;
      cacheList.appendChild(emptyLi);
      return;
    }

    filtered.forEach((item, index) => {
      const li = document.createElement("li");
      li.className = "cache-item";
      li.setAttribute("role", "option");
      li.setAttribute("tabindex", "0");
      li.dataset.claim = item.claim;

      li.innerHTML = `
        <p class="cache-claim-text">"${highlightMatch(item.claim, query)}"</p>
      `;

      li.addEventListener("click", () => {
        executeClaim(item.claim, true);
      });

      li.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          executeClaim(item.claim, true);
        }
      });

      cacheList.appendChild(li);
    });
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function highlightMatch(text, query) {
    if (!query) return escapeHtml(text);
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return escapeHtml(text).replace(regex, '<mark class="dropdown-match">$1</mark>');
  }

  function showDropdown() {
    if (cacheDropdown) {
      renderCacheList(searchInput ? searchInput.value : "");
      cacheDropdown.style.display = "block";
    }
  }

  function hideDropdown() {
    if (cacheDropdown) {
      cacheDropdown.style.display = "none";
    }
  }

  function executeClaim(rawClaim, isExplicitCached = false) {
    const claim = (rawClaim || "").trim();
    if (!claim) {
      if (searchInput) searchInput.focus();
      return;
    }

    // Check if entered claim matches one of the cached claims
    const matchesCache = isExplicitCached || CACHED_CLAIMS.some(c => c.claim && c.claim.toLowerCase() === claim.toLowerCase());

    const token = sessionStorage.getItem("tm_token") || localStorage.getItem("token");
    const isGuest = !token;
    const hasUsedGuestClaim = localStorage.getItem("tm_guest_claim_used") === "1";

    if (isGuest && hasUsedGuestClaim && !matchesCache) {
      // Block new custom claim if guest quota used
      if (guestLimitNotice) {
        guestLimitNotice.style.display = "flex";
      }
      if (searchBar) {
        searchBar.classList.add("shake-error");
        setTimeout(() => searchBar.classList.remove("shake-error"), 600);
      }
      hideDropdown();
      return;
    }

    // Navigate to /app and start verification
    const targetUrl = new URL("/app", window.location.origin);
    targetUrl.searchParams.set("claim", claim);
    if (matchesCache) {
      targetUrl.searchParams.set("is_cached", "1");
    }
    window.location.href = targetUrl.toString();
  }

  // Event Listeners
  if (searchInput) {
    searchInput.addEventListener("focus", () => {
      showDropdown();
      if (guestLimitNotice) guestLimitNotice.style.display = "none";
    });

    searchInput.addEventListener("input", () => {
      showDropdown();
      if (guestLimitNotice) guestLimitNotice.style.display = "none";
    });

    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        executeClaim(searchInput.value, false);
      } else if (e.key === "Escape") {
        hideDropdown();
      }
    });
  }

  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      executeClaim(searchInput ? searchInput.value : "", false);
    });
  }

  if (dismissNoticeBtn) {
    dismissNoticeBtn.addEventListener("click", () => {
      if (guestLimitNotice) guestLimitNotice.style.display = "none";
      if (searchInput) {
        searchInput.focus();
        showDropdown();
      }
    });
  }

  // Close dropdown when clicking outside
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#landingSearchForm") && !e.target.closest("#cacheDropdown")) {
      hideDropdown();
    }
  });

  /* ==========================================================================
     Interactive Story & Canvas Renderer (#scroll-story)
     ========================================================================== */
  initStoryScroll();
});

function initStoryScroll() {
  const scrollStory = document.getElementById("scroll-story");
  const storyCanvas = document.getElementById("story-canvas");
  const storyCard = document.getElementById("story-card");
  const storyTitle = document.getElementById("story-title");
  const storyText = document.getElementById("story-text");

  if (!scrollStory || !storyCanvas || !storyCard) return;

  const ctx = storyCanvas.getContext("2d");
  if (!ctx) return;

  const CARD1_TITLE = 'Why Trust <span class="font-serif-accent">US?</span>';
  const CARD1_TEXT =
    "We rely on AI which fetches from sources. The articles are real and the AI is instructed to explicitly fetch from that data. We link each source for every claim, showing clearly what is supported by the sources and what is not. After all these efforts AI can still be unreliable in some cases, we ask you to submit any errors or problems through the feedback form.";

  const CARD2_TITLE = 'How to <span class="font-serif-accent">Use</span> It?';
  const CARD2_TEXT =
    "Submit any claim that you heard or saw and the engine will start to verify it. Including specific dates, time periods and areas would help and focused claims are better than just vague opinions.";

  const COLOR_CYAN = [6, 182, 212];
  const COLOR_TEAL = [16, 185, 129];

  let currentPhase = 0;

  // Canvas scaling & particles
  let logicalWidth = 0;
  let logicalHeight = 0;
  let dpr = 1;
  const PARTICLE_COUNT = 45;
  let particles = [];

  function resizeCanvas() {
    const rect = storyCanvas.getBoundingClientRect();
    logicalWidth = rect.width || window.innerWidth;
    logicalHeight = rect.height || window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    storyCanvas.width = logicalWidth * dpr;
    storyCanvas.height = logicalHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    if (particles.length === 0) {
      initParticles();
    }
  }

  function initParticles() {
    particles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * logicalWidth,
        y: Math.random() * logicalHeight,
        size: Math.random() * 2.2 + 0.8,
        baseAlpha: Math.random() * 0.45 + 0.2,
        vx: (Math.random() - 0.5) * 0.35,
        vy: (Math.random() - 0.5) * 0.3,
        pulseSpeed: Math.random() * 1.5 + 0.8,
        pulseOffset: Math.random() * Math.PI * 2
      });
    }
  }

  // Scroll state tracking
  let currentP = 0;
  let scrollVelocity = 0;
  let lastScrollY = window.scrollY;
  let currentGlowX = null;

  function computeScrollProgress() {
    const rect = scrollStory.getBoundingClientRect();
    const maxScroll = scrollStory.offsetHeight - window.innerHeight;
    if (maxScroll <= 0) return 0;
    const scrolled = -rect.top;
    return Math.max(0, Math.min(1, scrolled / maxScroll));
  }

  function updateCard(p) {
    const isDesktop = window.innerWidth > 768;

    if (p < 0.45) {
      storyCard.style.transform = "translateX(0)";
      storyCard.style.opacity = "1";

      if (currentPhase !== 0) {
        currentPhase = 0;
        if (storyTitle) storyTitle.innerHTML = CARD1_TITLE;
        if (storyText) storyText.textContent = CARD1_TEXT;
      }
    } else if (p > 0.55) {
      storyCard.style.transform = isDesktop ? "translateX(108%)" : "translateX(0)";
      storyCard.style.opacity = "1";

      if (currentPhase !== 1) {
        currentPhase = 1;
        if (storyTitle) storyTitle.innerHTML = CARD2_TITLE;
        if (storyText) storyText.textContent = CARD2_TEXT;
      }
    } else {
      // Transition (0.45 <= p <= 0.55)
      const t = (p - 0.45) / 0.10;
      if (isDesktop) {
        storyCard.style.transform = `translateX(${t * 108}%)`;
      } else {
        storyCard.style.transform = "translateX(0)";
      }
      storyCard.style.opacity = "0.3";
    }
  }

  function onScroll() {
    const nowY = window.scrollY;
    const dy = nowY - lastScrollY;
    lastScrollY = nowY;
    scrollVelocity += dy * 0.04;

    currentP = computeScrollProgress();
    updateCard(currentP);
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", () => {
    resizeCanvas();
    updateCard(currentP);
  });

  // Initial setup
  resizeCanvas();
  currentP = computeScrollProgress();
  updateCard(currentP);
  currentGlowX = logicalWidth * (currentP > 0.55 ? 0.25 : 0.75);

  // Render loop
  function render(timestamp) {
    const now = (timestamp || performance.now()) * 0.001;

    // Damp scroll velocity
    scrollVelocity *= 0.90;

    // Clear logical canvas
    ctx.clearRect(0, 0, logicalWidth, logicalHeight);

    // Color remains cyan
    const pr = COLOR_CYAN[0];
    const pg = COLOR_CYAN[1];
    const pb = COLOR_CYAN[2];

    // Glow position & theme interpolation
    let glowFactor = 0;
    if (currentP < 0.45) {
      glowFactor = 0;
    } else if (currentP > 0.55) {
      glowFactor = 1;
    } else {
      glowFactor = (currentP - 0.45) / 0.10;
    }

    const targetGlowX = logicalWidth * (0.75 - glowFactor * 0.50);
    if (currentGlowX === null) {
      currentGlowX = targetGlowX;
    } else {
      currentGlowX += (targetGlowX - currentGlowX) * 0.08;
    }

    // Glow color remains cyan
    const gr = COLOR_CYAN[0];
    const gg = COLOR_CYAN[1];
    const gb = COLOR_CYAN[2];

    const isTransition = currentP >= 0.45 && currentP <= 0.55;
    const transitionIntensity = isTransition ? Math.sin(Math.PI * glowFactor) : 0;

    const baseRadius = Math.max(180, Math.min(logicalWidth, logicalHeight) * 0.38);
    const pulse = Math.sin(now * (isTransition ? 3.2 : 1.6)) * (15 + 16 * transitionIntensity);
    const glowRadius = Math.max(120, baseRadius + pulse);
    const glowY = logicalHeight * 0.5 + Math.sin(now * 1.1) * 12;

    // Draw large radial gradient glow ball
    const glowAlpha = 0.22 + 0.08 * transitionIntensity;
    const grad = ctx.createRadialGradient(currentGlowX, glowY, 0, currentGlowX, glowY, glowRadius);
    grad.addColorStop(0, `rgba(${gr}, ${gg}, ${gb}, ${glowAlpha})`);
    grad.addColorStop(0.35, `rgba(${gr}, ${gg}, ${gb}, ${glowAlpha * 0.55})`);
    grad.addColorStop(0.7, `rgba(${gr}, ${gg}, ${gb}, ${glowAlpha * 0.18})`);
    grad.addColorStop(1, `rgba(${gr}, ${gg}, ${gb}, 0)`);

    ctx.save();
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(currentGlowX, glowY, glowRadius, 0, Math.PI * 2);
    ctx.fill();

    // Core shimmer highlight
    const coreRadius = glowRadius * 0.3;
    const coreGrad = ctx.createRadialGradient(currentGlowX, glowY, 0, currentGlowX, glowY, coreRadius);
    coreGrad.addColorStop(0, `rgba(${gr}, ${gg}, ${gb}, ${glowAlpha * 0.75})`);
    coreGrad.addColorStop(1, `rgba(${gr}, ${gg}, ${gb}, 0)`);
    ctx.fillStyle = coreGrad;
    ctx.beginPath();
    ctx.arc(currentGlowX, glowY, coreRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Draw 45 drifting particles
    for (let i = 0; i < particles.length; i++) {
      const pt = particles[i];

      // Horizontal drift + gentle scroll shift
      pt.x += pt.vx + scrollVelocity * (pt.size * 0.35);
      pt.y += pt.vy;

      // Wrap around boundaries
      if (pt.x < 0) pt.x += logicalWidth;
      if (pt.x > logicalWidth) pt.x -= logicalWidth;
      if (pt.y < 0) pt.y += logicalHeight;
      if (pt.y > logicalHeight) pt.y -= logicalHeight;

      const pAlpha = Math.max(0.1, Math.min(0.9, pt.baseAlpha + Math.sin(now * pt.pulseSpeed + pt.pulseOffset) * 0.15));

      ctx.fillStyle = `rgba(${pr}, ${pg}, ${pb}, ${pAlpha})`;
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, pt.size, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(render);
  }

  requestAnimationFrame(render);
}
