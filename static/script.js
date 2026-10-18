document.addEventListener("DOMContentLoaded", () => {
    const loginScreen = document.getElementById("loginScreen");
    const mainApp = document.getElementById("mainApp");
    
    // --- Canvas Background Animation ---
    const canvas = document.getElementById('bg-canvas');
    let ctx, width, height, orbs = [], animationId;
    let initCanvas, animateCanvas, setupOrbs;
    
    if (canvas) {
        ctx = canvas.getContext('2d');
        
        class Orb {
            constructor(color, radiusBase) {
                this.x = Math.random() * window.innerWidth;
                this.y = Math.random() * window.innerHeight;
                this.vx = (Math.random() - 0.5) * 0.4;
                this.vy = (Math.random() - 0.5) * 0.4;
                this.radius = radiusBase;
                this.color = color;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < -this.radius) this.x = width + this.radius;
                if (this.x > width + this.radius) this.x = -this.radius;
                if (this.y < -this.radius) this.y = height + this.radius;
                if (this.y > height + this.radius) this.y = -this.radius;
            }
            draw() {
                const grad = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius);
                grad.addColorStop(0, this.color);
                grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
                ctx.fillStyle = grad;
                ctx.fillRect(this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2);
            }
        }

        setupOrbs = () => {
            orbs = [
                new Orb('rgba(6, 182, 212, 0.15)', 500),
                new Orb('rgba(245, 158, 11, 0.1)', 400),
                new Orb('rgba(6, 182, 212, 0.12)', 600)
            ];
        };

        initCanvas = () => {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
            setupOrbs();
        };

        animateCanvas = () => {
            ctx.fillStyle = '#0b0b0f';
            ctx.fillRect(0, 0, width, height);
            ctx.globalCompositeOperation = 'screen';
            orbs.forEach(orb => { orb.update(); orb.draw(); });
            ctx.globalCompositeOperation = 'source-over';
            animationId = requestAnimationFrame(animateCanvas);
        };

        window.addEventListener('resize', initCanvas);
    }

    const startAnimation = () => {
        if (canvas && initCanvas && animateCanvas) {
            initCanvas();
            animateCanvas();
        }
    };
    const stopAnimation = () => {
        if (animationId) cancelAnimationFrame(animationId);
    };

    function updateGuestClaimGate() {
      const token = sessionStorage.getItem("tm_token") || localStorage.getItem("token");
      const wrapper = document.getElementById("guestClaimWrapper");
      const verifyBtn = document.getElementById("verifyBtn");
      if (!wrapper) return;
      if (!token && localStorage.getItem("tm_guest_claim_used") === "1" && !window._tm_bypass_guest_check) {
        wrapper.classList.add("claim-used");
        wrapper.setAttribute("data-tooltip", "Sign up to analyze more claims");
        if (verifyBtn) {
          verifyBtn.disabled = true;
        }
      } else {
        wrapper.classList.remove("claim-used");
        wrapper.removeAttribute("data-tooltip");
        if (verifyBtn) {
          verifyBtn.disabled = false;
        }
      }
    }

    if (canvas) {
        startAnimation();
    } else {
        stopAnimation();
    }
    updateGuestClaimGate();

    // Pending email state for verification & resend
    let pendingEmail = "";

    window.switchAuthTab = function(tab) {
        const tabLogin = document.getElementById("tabLogin");
        const tabSignup = document.getElementById("tabSignup");
        const authViewLogin = document.getElementById("authViewLogin");
        const authViewSignup = document.getElementById("authViewSignup");
        const authViewVerify = document.getElementById("authViewVerify");
        const authTabs = document.getElementById("authTabs");
        const authSubtitle = document.getElementById("authSubtitle");
        const loginError = document.getElementById("loginError");
        const signupError = document.getElementById("signupError");
        const verifyError = document.getElementById("verifyError");
        const resendFeedback = document.getElementById("resendFeedback");

        if (loginError) loginError.style.display = "none";
        if (signupError) signupError.style.display = "none";
        if (verifyError) verifyError.style.display = "none";
        if (resendFeedback) resendFeedback.style.display = "none";

        if (tab === "login") {
            if (authTabs) authTabs.style.display = "flex";
            if (tabLogin) tabLogin.classList.add("active");
            if (tabSignup) tabSignup.classList.remove("active");
            if (authViewLogin) authViewLogin.style.display = "block";
            if (authViewSignup) authViewSignup.style.display = "none";
            if (authViewVerify) authViewVerify.style.display = "none";
            if (authSubtitle) {
                authSubtitle.textContent = "Login";
                authSubtitle.style.color = "var(--accent-teal)";
            }
        } else if (tab === "signup") {
            if (authTabs) authTabs.style.display = "flex";
            if (tabSignup) tabSignup.classList.add("active");
            if (tabLogin) tabLogin.classList.remove("active");
            if (authViewSignup) authViewSignup.style.display = "block";
            if (authViewLogin) authViewLogin.style.display = "none";
            if (authViewVerify) authViewVerify.style.display = "none";
            if (authSubtitle) {
                authSubtitle.textContent = "Sign Up";
                authSubtitle.style.color = "var(--accent-teal)";
            }
        } else if (tab === "verify") {
            if (tabLogin) tabLogin.classList.remove("active");
            if (tabSignup) tabSignup.classList.remove("active");
            if (authViewLogin) authViewLogin.style.display = "none";
            if (authViewSignup) authViewSignup.style.display = "none";
            if (authViewVerify) authViewVerify.style.display = "block";
            if (authSubtitle) {
                authSubtitle.textContent = "Verification";
                authSubtitle.style.color = "var(--accent-teal)";
            }
        }
    };

    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("tab") === "signup") {
        window.switchAuthTab("signup");
    }

    // Input Label Glow Sync across all login/signup/verify forms
    const authInputs = document.querySelectorAll('.login-wrapper input');
    authInputs.forEach(input => {
        input.addEventListener('focus', (e) => {
            const wrapper = e.target.closest('.input-wrapper');
            if (wrapper) {
                const label = wrapper.querySelector('label');
                if (label) label.style.color = '#06B6D4';
            }
        });
        input.addEventListener('blur', (e) => {
            const wrapper = e.target.closest('.input-wrapper');
            if (wrapper) {
                const label = wrapper.querySelector('label');
                if (label) label.style.color = 'var(--text-dim)';
            }
        });
    });

    // ── Login Form Handler ──
    const loginForm = document.getElementById('login-form');
    const loginBtn = document.getElementById('loginBtn');
    const loginBtnText = document.getElementById('loginBtnText');
    const authSubtitle = document.getElementById('authSubtitle');
    const loginError = document.getElementById('loginError');

    const hideLoginError = () => { if (loginError) loginError.style.display = "none"; };
    if (loginForm) {
        const opIdInput = document.getElementById('operator-id');
        const passkeyInput = document.getElementById('passkey');
        if (opIdInput) opIdInput.addEventListener('input', hideLoginError);
        if (passkeyInput) passkeyInput.addEventListener('input', hideLoginError);

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = opIdInput ? opIdInput.value.trim() : '';
            const password = passkeyInput ? passkeyInput.value : '';
            if (!email || !password) return;

            if (loginBtn) loginBtn.style.pointerEvents = 'none';
            if (loginBtnText) loginBtnText.textContent = 'Authenticating...';
            if (loginError) loginError.style.display = 'none';

            try {
                const res = await fetch("/api/login", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password })
                });
                
                if (res.ok) {
                    const data = await res.json();
                    sessionStorage.setItem("tm_token", data.token);
                    localStorage.setItem("token", data.token);
                    updateGuestClaimGate();
                    
                    if (loginBtn) loginBtn.classList.add('success');
                    if (loginBtnText) loginBtnText.textContent = 'Access Granted';
                    if (authSubtitle) {
                        authSubtitle.textContent = 'Connection Established';
                        authSubtitle.style.color = 'var(--accent-amber)';
                    }
                    
                    setTimeout(() => {
                        window.location.href = '/static/index.html';
                    }, 1500);
                } else {
                    const data = await res.json().catch(() => ({}));
                    if (loginError) {
                        loginError.style.display = "block";
                        loginError.textContent = data.error || "Invalid Email or Password";
                    }
                    if (loginBtn) loginBtn.style.pointerEvents = 'auto';
                    if (loginBtnText) loginBtnText.textContent = 'Initialize Connection';
                }
            } catch (err) {
                console.error(err);
                if (loginError) {
                    loginError.style.display = "block";
                    loginError.textContent = "Network error";
                }
                if (loginBtn) loginBtn.style.pointerEvents = 'auto';
                if (loginBtnText) loginBtnText.textContent = 'Initialize Connection';
            }
        });
    }

    // ── Sign Up Form Handler ──
    const signupForm = document.getElementById('signup-form');
    const signupBtn = document.getElementById('signupBtn');
    const signupBtnText = document.getElementById('signupBtnText');
    const signupError = document.getElementById('signupError');

    const hideSignupError = () => { if (signupError) signupError.style.display = "none"; };
    if (signupForm) {
        const emailInput = document.getElementById('signup-email');
        const passwordInput = document.getElementById('signup-password');

        if (emailInput) emailInput.addEventListener('input', hideSignupError);
        if (passwordInput) passwordInput.addEventListener('input', hideSignupError);

        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = emailInput ? emailInput.value.trim() : '';
            const password = passwordInput ? passwordInput.value : '';

            if (!email || !password) return;

            if (signupBtn) signupBtn.style.pointerEvents = 'none';
            if (signupBtnText) signupBtnText.textContent = 'Creating Account...';
            if (signupError) signupError.style.display = 'none';

            try {
                const res = await fetch("/api/register", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password })
                });

                const data = await res.json().catch(() => ({}));

                if (res.ok || res.status === 201) {
                    if (data.token) {
                        sessionStorage.setItem("tm_token", data.token);
                        localStorage.setItem("token", data.token);
                        updateGuestClaimGate();
                        setTimeout(() => {
                            window.location.href = '/static/index.html';
                        }, 1500);
                    } else {
                        pendingEmail = email;
                        const verifyEmailDisplay = document.getElementById('verifyEmailDisplay');
                        if (verifyEmailDisplay) verifyEmailDisplay.textContent = email;

                        if (signupBtn) signupBtn.style.pointerEvents = 'auto';
                        if (signupBtnText) signupBtnText.textContent = 'Create Account';

                        window.switchAuthTab('verify');
                    }
                } else {
                    if (signupError) {
                        signupError.style.display = "block";
                        signupError.textContent = data.error || "Registration failed. Please try again.";
                    }
                    if (signupBtn) signupBtn.style.pointerEvents = 'auto';
                    if (signupBtnText) signupBtnText.textContent = 'Create Account';
                }
            } catch (err) {
                console.error(err);
                if (signupError) {
                    signupError.style.display = "block";
                    signupError.textContent = "Network error. Please try again.";
                }
                if (signupBtn) signupBtn.style.pointerEvents = 'auto';
                if (signupBtnText) signupBtnText.textContent = 'Create Account';
            }
        });
    }

    // ── Verify Form Handler ──
    const verifyForm = document.getElementById('verify-form');
    const verifyBtnSubmit = document.getElementById('verifyBtnSubmit');
    const verifyBtnText = document.getElementById('verifyBtnText');
    const verifyError = document.getElementById('verifyError');

    const hideVerifyError = () => { if (verifyError) verifyError.style.display = "none"; };
    if (verifyForm) {
        const codeInput = document.getElementById('verify-code');
        if (codeInput) codeInput.addEventListener('input', hideVerifyError);

        verifyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const code = codeInput ? codeInput.value.trim() : '';
            const verifyEmailDisplay = document.getElementById('verifyEmailDisplay');
            const email = pendingEmail || (verifyEmailDisplay ? verifyEmailDisplay.textContent.trim() : '');

            if (!code || !email) {
                if (verifyError) {
                    verifyError.style.display = 'block';
                    verifyError.textContent = 'Please enter the 6-digit verification code.';
                }
                return;
            }

            if (verifyBtnSubmit) verifyBtnSubmit.style.pointerEvents = 'none';
            if (verifyBtnText) verifyBtnText.textContent = 'Verifying...';
            if (verifyError) verifyError.style.display = 'none';

            try {
                const res = await fetch("/api/verify-email", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, code })
                });

                const data = await res.json().catch(() => ({}));

                if (res.ok) {
                    sessionStorage.setItem("tm_token", data.token);
                    localStorage.setItem("token", data.token);
                    updateGuestClaimGate();

                    if (verifyBtnSubmit) verifyBtnSubmit.classList.add('success');
                    if (verifyBtnText) verifyBtnText.textContent = 'Verified';
                    if (authSubtitle) {
                        authSubtitle.textContent = 'Connection Established';
                        authSubtitle.style.color = 'var(--accent-amber)';
                    }

                    setTimeout(() => {
                        window.location.href = '/static/index.html';
                    }, 1500);
                } else {
                    if (verifyError) {
                        verifyError.style.display = "block";
                        verifyError.textContent = data.error || "Invalid verification code";
                    }
                    if (verifyBtnSubmit) verifyBtnSubmit.style.pointerEvents = 'auto';
                    if (verifyBtnText) verifyBtnText.textContent = 'Verify & Continue';
                }
            } catch (err) {
                console.error(err);
                if (verifyError) {
                    verifyError.style.display = "block";
                    verifyError.textContent = "Network error. Please try again.";
                }
                if (verifyBtnSubmit) verifyBtnSubmit.style.pointerEvents = 'auto';
                if (verifyBtnText) verifyBtnText.textContent = 'Verify & Continue';
            }
        });
    }

    // ── Resend Code Handler ──
    window.resendCode = async function() {
        const verifyEmailDisplay = document.getElementById('verifyEmailDisplay');
        const email = pendingEmail || (verifyEmailDisplay ? verifyEmailDisplay.textContent.trim() : '');
        const resendBtn = document.getElementById('resendCodeBtn');
        const resendFeedback = document.getElementById('resendFeedback');
        const verifyError = document.getElementById('verifyError');

        if (verifyError) verifyError.style.display = 'none';
        if (!email) {
            if (verifyError) {
                verifyError.style.display = 'block';
                verifyError.textContent = 'Email address missing. Please go back to Sign Up.';
            }
            return;
        }

        if (resendBtn) {
            resendBtn.disabled = true;
            resendBtn.style.pointerEvents = 'none';
        }
        if (resendFeedback) {
            resendFeedback.style.display = 'block';
            resendFeedback.style.color = 'var(--text-muted)';
            resendFeedback.textContent = 'Sending new code...';
        }

        try {
            const res = await fetch("/api/resend-code", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });

            const data = await res.json().catch(() => ({}));

            if (res.ok) {
                if (resendFeedback) {
                    resendFeedback.style.display = 'block';
                    resendFeedback.style.color = 'var(--success)';
                    resendFeedback.textContent = 'Verification code sent to your email!';
                }
            } else {
                if (resendFeedback) {
                    resendFeedback.style.display = 'block';
                    resendFeedback.style.color = 'var(--danger)';
                    resendFeedback.textContent = data.error || 'Failed to resend code.';
                }
            }
        } catch (err) {
            console.error(err);
            if (resendFeedback) {
                resendFeedback.style.display = 'block';
                resendFeedback.style.color = 'var(--danger)';
                resendFeedback.textContent = 'Network error. Please try again.';
            }
        } finally {
            setTimeout(() => {
                if (resendBtn) {
                    resendBtn.disabled = false;
                    resendBtn.style.pointerEvents = 'auto';
                }
            }, 3000);
        }
    };

    // ── Screen Wake Lock ────────────────────────────────────
    let wakeLock = null;

    async function requestWakeLock() {
      if ('wakeLock' in navigator) {
        try {
          wakeLock = await navigator.wakeLock.request('screen');
          console.log('[Wake Lock] Acquired — screen will stay on.');

          wakeLock.addEventListener('release', () => {
            console.log('[Wake Lock] Released.');
            wakeLock = null;
          });
        } catch (err) {
          console.warn('[Wake Lock] Failed to acquire:', err.message);
          wakeLock = null;
        }
      }
    }

    async function releaseWakeLock() {
      if (wakeLock) {
        try {
          await wakeLock.release();
          console.log('[Wake Lock] Explicitly released.');
        } catch (err) {
          console.warn('[Wake Lock] Release failed:', err.message);
        }
        wakeLock = null;
      }
    }

    window.dismissTermsBanner = function() {
      const banner = document.getElementById('termsBanner');
      if (banner) {
        banner.style.opacity = '0';
        banner.style.transform = 'translate(-50%, calc(-50% - 10px))';
        banner.style.transition = 'all 0.3s ease';
        setTimeout(() => banner.remove(), 300);
      if(document.getElementById('termsOverlay')) document.getElementById('termsOverlay').remove();
      }
    }


    const elements = {
      claimInput: document.getElementById("claimInput"),
      verifyBtn: document.getElementById("verifyBtn"),
      guestClaimWrapper: document.getElementById("guestClaimWrapper"),
      verifyLoader: document.getElementById("verifyLoader"),
      btnText: document.querySelector("#verifyBtn .btn-text"),
      loadingStatus: document.getElementById("loadingStatus"),
      initialState: document.getElementById("initialState"),
      dashboard: document.getElementById("dashboard"),
      
      pipelineTracker: document.getElementById("pipelineTracker"),
      
      verdictBanner: document.getElementById("verdictBanner"),
      verdictClaim: document.getElementById("verdictClaim"),
      verdictValue: document.getElementById("verdictValue"),
      verdictOneLine: document.getElementById("verdictOneLine"),
      confidenceBadge: document.getElementById("confidenceBadge"),
      
      fullReasoning: document.getElementById("fullReasoning"),
      whatIsTrue: document.getElementById("whatIsTrue"),
      whatIsFalse: document.getElementById("whatIsFalse"),
      whatIsUnclear: document.getElementById("whatIsUnclear"),
      
      hiddenStoriesContainer: document.getElementById("hiddenStoriesContainer")
    };

    // Re-acquire wake lock when user switches back to the tab during verification
    document.addEventListener('visibilitychange', async () => {
      if (document.visibilityState === 'visible' && wakeLock === null) {
        const isRunning = elements.verifyBtn && elements.verifyBtn.disabled;
        if (isRunning) {
          await requestWakeLock();
        }
      }
    });

    if (elements.verifyBtn) {
      elements.verifyBtn.addEventListener("click", verifyClaim);
    }
    if (elements.claimInput) {
      elements.claimInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") verifyClaim();
      });
    }

    // Toggle Accordion function
    window.toggleAccordion = function(element) {
      const parent = element.parentElement;
      parent.classList.toggle('active');
    };

    window.toggleBackgroundSources = function() {
      const accordion = document.getElementById("backgroundAccordion");
      const label = document.getElementById("backgroundToggleLabel");
      if (!accordion) return;
      const isActive = accordion.classList.contains("active");

      if (isActive) {
          accordion.classList.remove("active");
          if (label) label.textContent = "∨";
      } else {
          accordion.classList.add("active");
          if (label) label.textContent = "∧";
      }
    };

    window.toggleSourceCard = function(btn) {
      if (!btn) return;
      const row = btn.closest('tr');
      if (!row) return;
      const isExpanded = row.classList.contains('expanded');
      if (isExpanded) {
        row.classList.remove('expanded');
        btn.textContent = 'Show more ▼';
      } else {
        row.classList.add('expanded');
        btn.textContent = 'Show less ▲';
      }
    };

    function showErrorPanel(detail) {
        // Hide the dashboard and initial state if visible
        elements.dashboard.style.display = "none";
        stopScrambling();
      document.getElementById('skeletonContainer').style.display = 'none';
        const rc = document.getElementById('resultsContainer');
        if (rc) rc.style.display = "none";

        // Show or reuse the error panel
        let errorPanel = document.getElementById("errorPanel");
        if (!errorPanel) {
            errorPanel = document.createElement("div");
            errorPanel.id = "errorPanel";
            // Insert it into main-content, after the top-bar
            const mainContent = document.querySelector(".main-content");
            mainContent.appendChild(errorPanel);
        }

        errorPanel.style.display = "flex";
        errorPanel.innerHTML = `
            <div class="error-panel-icon">✕</div>
            <div class="error-panel-body">
                <div class="error-panel-title">Something went wrong</div>
                <div class="error-panel-msg">
                    An error occurred while verifying this claim. Please try
                    again. If the problem persists, refresh the page and
                    resubmit.
                </div>
                <div class="error-panel-detail">${detail || ""}</div>
                <button class="btn btn-primary error-panel-retry"
                        onclick="dismissError()">
                    Try Again
                </button>
            </div>
        `;
    }

    function dismissError() {
        const errorPanel = document.getElementById("errorPanel");
        if (errorPanel) errorPanel.style.display = "none";
        elements.initialState.style.display = "block";
    }

    function buildSourceRow(sa) {
      const stance = sa.stance || "UNKNOWN";
      let sColor = "var(--text-muted)";
      let barColor = "var(--text-muted)";
      if (stance === "SUPPORTS") { sColor = "var(--success)"; barColor = "var(--success)"; }
      if (stance === "CONTRADICTS") { sColor = "var(--danger)"; barColor = "var(--danger)"; }
      if (stance === "PARTIALLY_SUPPORTS") { sColor = "var(--warning)"; barColor = "var(--warning)"; }

      let confidenceStr = 'N/A';
      let confidencePct = 0;
      if (typeof sa.stance_confidence === 'number') {
        confidencePct = Math.round(sa.stance_confidence * 100);
        if (sa.stance_confidence >= 0.8) confidenceStr = 'Very High';
        else if (sa.stance_confidence >= 0.6) confidenceStr = 'High';
        else if (sa.stance_confidence >= 0.4) confidenceStr = 'Medium';
        else if (sa.stance_confidence >= 0.2) confidenceStr = 'Low';
        else confidenceStr = 'Very Low';
      }

      return `
        <tr>
          <td>
            <div style="font-weight: 600; color: var(--text-main); margin-bottom: 0.25rem;">${sa.source_name || "Unknown"}</div>
            <a href="${sa.url || "#"}" target="_blank"
               style="font-size: 0.8rem; color: var(--accent); text-decoration: none;">
              View Source ↗
            </a>
            ${sa.archive_url ? `<br><a href="${sa.archive_url}" target="_blank" style="font-size: 0.75rem; color: var(--warning); text-decoration: none;">View Archive ↗</a>` : ''}
          </td>
          <td>
            <span class="bloc-stance" style="background: rgba(255,255,255,0.05); color: ${sColor}; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.7rem;">
              ${stance.replace('_', ' ')}
            </span>
          </td>
          <td>
            <div class="confidence-cell">
              <div class="confidence-bar-bg">
                <div class="confidence-bar-fill" style="width: ${confidencePct}%; background: ${barColor};"></div>
              </div>
              <span class="conf-label">${confidenceStr}</span>
            </div>
          </td>
          <td style="font-size: 0.85rem; color: var(--text-muted); max-width: 300px; line-height: 1.5;">
            ${sa.what_emphasized || "N/A"}
          </td>
          <td class="source-card-toggle-cell">
            <button class="source-card-toggle" onclick="toggleSourceCard(this)">
              Show more ▼
            </button>
          </td>
        </tr>
      `;
    }

    async function finalizeVerification() {
      elements.btnText.style.display = "block";
      elements.verifyLoader.style.display = "none";
      elements.verifyBtn.disabled = false;
      elements.verifyBtn.style.display = 'flex';
      elements.loadingStatus.textContent = "";
      elements.loadingStatus.style.fontSize = '';
      elements.loadingStatus.style.opacity = '';
      elements.pipelineTracker.style.display = 'none';
      updateGuestClaimGate();
      releaseWakeLock(); // Do not await, prevents UI hang if API never resolves
    }

    
    // --- Scramble Text Effect ---
    let scrambleInterval = null;
    function startScrambling(el, targetText) {
        const chars = '!<>-_\\/[]{}—=+*^?#_';
        if (scrambleInterval) clearInterval(scrambleInterval);
        
        scrambleInterval = setInterval(() => {
            let output = '';
            for (let i = 0; i < targetText.length; i++) {
                if (targetText[i] === ' ') {
                    output += ' ';
                    continue;
                }
                // Scramble 10% of characters randomly for active effect
                if (Math.random() < 0.1) {
                    output += chars[Math.floor(Math.random() * chars.length)];
                } else {
                    output += targetText[i];
                }
            }
            el.textContent = output;
        }, 60);
    }
    
    function stopScrambling() {
        if (scrambleInterval) {
            clearInterval(scrambleInterval);
            scrambleInterval = null;
        }
    }

    async function verifyClaim() {
      const token = sessionStorage.getItem("tm_token") || localStorage.getItem("token");
      const isGuest = !token;

      if (isGuest && localStorage.getItem("tm_guest_claim_used") === "1" && !window._tm_bypass_guest_check) {
        return;
      }

      const claim = elements.claimInput.value.trim();
      if (!claim) return;

      // Acquire wake lock to keep screen on during 2–4 min verification
      await requestWakeLock();

      elements.btnText.style.display = "none";
      elements.verifyLoader.style.display = "block";
      elements.verifyBtn.disabled = true;
      elements.verifyBtn.style.display = 'none';
      elements.verdictOneLine.textContent = "Processing Intelligence Report";
      startScrambling(elements.verdictOneLine, "PROCESSING INTELLIGENCE REPORT...");
      elements.verdictValue.style.display = 'none';
      elements.confidenceBadge.style.display = 'none';
      elements.verdictClaim.style.display = 'none';
      elements.verdictBanner.classList.add('verdict-processing-state');
      elements.verdictBanner.style.boxShadow = '';
      elements.verdictBanner.style.borderColor = '';


      // Show skeleton and pipeline tracker
      elements.dashboard.style.display = 'grid';
      document.getElementById('skeletonContainer').style.display = 'block';
      const rc = document.getElementById('resultsContainer');
      if (rc) rc.style.display = 'none';
      elements.pipelineTracker.style.display = 'block';
      
      elements.loadingStatus.style.fontSize = '0.75rem';
      elements.loadingStatus.style.opacity = '0.5';

      const STAGE_MESSAGES = {
        "idle": "Initializing...",
        "classifying": "Classifying claim scope...",
        "decomposing_temporal": "Breaking down temporal bounds...",
        "generating_queries": "Generating search vectors...",
        "fetching_primary": "Fetching targeted queries...",
        "fetching_regional": "Fetching regional media...",
        "deduplicating": "Aggregating evidence...",
        "analyzing_primary": "Analyzing primary evidence...",
        "cross_referencing": "Cross-referencing stances...",
        "extracting_stories": "Extracting hidden narratives...",
        "weighing_contradictions": "Weighing contradictions...",
        "synthesizing_verdict": "Calculating final verdict..."
      };

      const FUN_MESSAGES = [
        "Still thinking...",
        "Reading between the lines...",
        "Decoding diplomatic speak...",
        "Cross-referencing state media...",
        "Following the money...",
        "Checking bias filters...",
        "Synthesizing the truth..."
      ];

      let currentStage = "idle";
      let stageCounter = 0;
      let funMsgIdx = 0;

      const requestId = crypto.randomUUID();

      // Update pipeline tracker
      const PIPELINE_ORDER = [
        "classifying", "decomposing_temporal", "generating_queries", 
        "fetching_primary", "fetching_regional", "deduplicating", 
        "analyzing_primary", "cross_referencing", "extracting_stories", 
        "weighing_contradictions", "synthesizing_verdict"
      ];

      function updatePipelineTracker(backendStage) {
        const mappedStage = backendStage;
        const steps = document.querySelectorAll('.pipeline-step');
        const currentIdx = PIPELINE_ORDER.indexOf(mappedStage);
        
        steps.forEach((step, idx) => {
          step.classList.remove('active', 'completed');
          const textEl = step.querySelector('.step-text');
          const originalText = textEl.getAttribute('data-text') || textEl.textContent;
          textEl.setAttribute('data-text', originalText.replace(/\.\.\.$/, ''));
          
          if (idx < currentIdx) {
            step.classList.add('completed');
            step.querySelector('.step-indicator').textContent = '◉';
            textEl.textContent = textEl.getAttribute('data-text');
          } else if (idx === currentIdx) {
            step.classList.add('active');
            step.querySelector('.step-indicator').textContent = '○';
            textEl.textContent = textEl.getAttribute('data-text') + '...';
          } else {
            step.querySelector('.step-indicator').textContent = '○';
            textEl.textContent = textEl.getAttribute('data-text');
          }
        });
      }

      const pollStatus = async () => {
        try {
          const statusUrl = isGuest
            ? "/api/status?request_id=" + requestId + "&guest=1"
            : "/api/status?request_id=" + requestId;
          const statusHeaders = isGuest ? {} : { "Authorization": "Bearer " + token };

          const res = await fetch(statusUrl, {
            headers: statusHeaders
          });
          if (res.status === 401) {
            if (!isGuest) {
              sessionStorage.removeItem("tm_token");
              localStorage.removeItem("token");
              window.location.reload();
              return;
            }
          }
          if (res.ok) {
            const data = await res.json();
            
            if (data.stage === "completed" || data.stage === "failed") {
              clearInterval(mInt);
              await finalizeVerification();
              
              if (data.stage === "failed" || (data.result && data.result.error)) {
                const errData = data.result || data;
                if (errData.verdict === "TIMEOUT") {
                   showErrorPanel(errData.verdict_data?.one_line_verdict || "The system is under heavy load. Please try again in a few minutes.");
                } else {
                   showErrorPanel(errData.verdict_data?.one_line_verdict || errData.error || "Verification failed");
                }
                return;
              }
              
              const resultData = data.result;
              if (resultData && resultData.is_geopolitical === false) {
                elements.initialState.innerHTML = '';
                
                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('width', '80');
                svg.setAttribute('height', '80');
                svg.setAttribute('viewBox', '0 0 24 24');
                svg.setAttribute('fill', 'none');
                svg.setAttribute('stroke', 'var(--danger)');
                svg.setAttribute('stroke-width', '1.5');
                svg.setAttribute('stroke-linecap', 'round');
                svg.setAttribute('stroke-linejoin', 'round');
                svg.style.marginBottom = '1.5rem';
                svg.innerHTML = '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>';
                
                const h2 = document.createElement('h2');
                h2.style.fontSize = '2rem';
                h2.style.color = 'var(--danger)';
                h2.style.marginBottom = '0.5rem';
                h2.textContent = 'Out of Scope';
                
                const p = document.createElement('p');
                p.style.fontSize = '1.1rem';
                p.style.maxWidth = '600px';
                p.style.margin = '0 auto';
                p.style.color = 'var(--text-muted)';
                p.textContent = resultData.rejection_reason;
                
                elements.initialState.appendChild(svg);
                elements.initialState.appendChild(h2);
                elements.initialState.appendChild(p);

                elements.initialState.style.display = "block";
                elements.dashboard.style.display = "none";

                const isCachedRun = window._tm_bypass_guest_check;
                if (isGuest && !isCachedRun) {
                  localStorage.setItem("tm_guest_claim_used", "1");
                  updateGuestClaimGate();
                }
                return;
              }
      
              renderDashboard(resultData);
              const vdata = (resultData && resultData.verdict_data) || {};
              const finalVerdict = (resultData && resultData.verdict) || vdata.verdict;
              const isCachedRun = window._tm_bypass_guest_check;
              if (isGuest && !isCachedRun && finalVerdict !== "ERROR" && finalVerdict !== "TIMEOUT" && finalVerdict !== "ANALYSIS_FAILED") {
                localStorage.setItem("tm_guest_claim_used", "1");
                updateGuestClaimGate();
              }
              return;
            }

            if (data.stage !== currentStage) {
              currentStage = data.stage;
              stageCounter = 0;
              elements.loadingStatus.textContent = STAGE_MESSAGES[currentStage] || "Processing...";
              updatePipelineTracker(currentStage);
            } else {
              stageCounter++;
              if (stageCounter > 2) {
                elements.loadingStatus.textContent = FUN_MESSAGES[funMsgIdx % FUN_MESSAGES.length];
                funMsgIdx++;
              }
            }
          }
        } catch (e) {
            console.error(e);
        }
      };

      elements.loadingStatus.textContent = STAGE_MESSAGES[currentStage];
      const mInt = setInterval(pollStatus, 1500);

      const existingError = document.getElementById("errorPanel");
      if (existingError) existingError.style.display = "none";
      elements.initialState.style.display = "none";

      try {
        const verifyUrl = isGuest ? "/api/guest-verify" : "/api/verify";
        const verifyHeaders = { "Content-Type": "application/json" };
        if (!isGuest) {
          verifyHeaders["Authorization"] = "Bearer " + token;
        }

        const res = await fetch(verifyUrl, {
          method: "POST",
          headers: verifyHeaders,
          body: JSON.stringify({ claim, request_id: requestId })
        });
        
        if (res.status === 401) {
          if (!isGuest) {
            sessionStorage.removeItem("tm_token");
            localStorage.removeItem("token");
            window.location.reload();
            return;
          }
        }
        if (!res.ok && res.status !== 202) {
          clearInterval(mInt);
          await finalizeVerification();
          if (res.status === 503) {
            const errData = await res.json();
            showErrorPanel(
              errData.verdict_data?.one_line_verdict || 
              "The system is under heavy load. Please try again in a few minutes."
            );
            return;
          }
          throw new Error("Failed to start verification");
        }

        if (res.status === 200) {
            const data = await res.json();
            if (data.stage === "completed" || data.result) {
                clearInterval(mInt);
                await finalizeVerification();
                renderDashboard(data.result || data);
                return;
            }
        }
        
      } catch (err) {
        clearInterval(mInt);
        await finalizeVerification();
        showErrorPanel(err.message);
      }
    }

    function renderDashboard(data) {
      try {
      stopScrambling();
      document.getElementById('skeletonContainer').style.display = 'none';
      const rc = document.getElementById('resultsContainer');
      if (rc) rc.style.display = 'grid';
      // Check for infrastructure failure — show error panel, not dashboard
      const vdata = data.verdict_data || {};
      
      if (vdata.verdict === "TIMEOUT" || data.verdict === "TIMEOUT") {
          showErrorPanel(
              "The analysis timed out due to heavy load. " +
              "Please wait a few minutes and resubmit."
          );
          return;
      }
      
      if (vdata.verdict === "ANALYSIS_FAILED" || data.verdict === "ANALYSIS_FAILED") {
          showErrorPanel(
              "API capacity was temporarily exhausted. All available models " +
              "were rate-limited simultaneously. Please wait 2-3 minutes " +
              "and resubmit your claim."
          );
          return;   // Do not render the dashboard for infra failures
      }

      elements.initialState.style.display = "none";
      elements.dashboard.style.display = "grid";
      
      // Verdict Banner
      elements.verdictBanner.classList.remove('verdict-processing-state');
      document.getElementById('verdictClaim').textContent = `"${data.original_claim || data.claim || ''}"`;
      elements.verdictClaim.style.display = 'block';
      
      elements.verdictValue.style.display = 'block';
      elements.confidenceBadge.style.display = 'inline-block';

      const rawVerdict = (vdata.verdict || data.verdict || "UNVERIFIABLE").replace(/_/g, " ");
      elements.verdictValue.textContent = rawVerdict;
      elements.verdictOneLine.textContent = vdata.one_line_verdict || "No clear verdict generated.";
      elements.confidenceBadge.textContent = `${vdata.confidence_label || 'Low'} Confidence`;
      
      const v = rawVerdict.trim().toUpperCase();
      let textColorClass, bgClass, verdictGlow;

      if (v.includes("SUPPORTED") && !v.includes("PARTIALLY")) {
        textColorClass = "verdict-text-success";
        bgClass = "confidence-bg-success";
        verdictGlow = "0 0 40px rgba(34, 197, 94, 0.1)";
        elements.verdictBanner.style.borderColor = "rgba(34, 197, 94, 0.3)";
      } else if (v.includes("PARTIALLY")) {
        textColorClass = "verdict-text-warning";
        bgClass = "confidence-bg-warning";
        verdictGlow = "0 0 40px rgba(234, 179, 8, 0.1)";
        elements.verdictBanner.style.borderColor = "rgba(234, 179, 8, 0.3)";
      } else if (v.includes("CONTRADICTED")) {
        textColorClass = "verdict-text-danger";
        bgClass = "confidence-bg-danger";
        verdictGlow = "0 0 40px rgba(239, 68, 68, 0.1)";
        elements.verdictBanner.style.borderColor = "rgba(239, 68, 68, 0.3)";
      } else {
        textColorClass = "verdict-text-warning";
        bgClass = "confidence-bg-warning";
        verdictGlow = "0 0 40px rgba(234, 179, 8, 0.08)";
        elements.verdictBanner.style.borderColor = "rgba(234, 179, 8, 0.2)";
      }

      elements.verdictValue.className = 'verdict-value ' + textColorClass;
      elements.confidenceBadge.className = 'confidence-badge ' + bgClass;
      elements.verdictBanner.style.boxShadow = verdictGlow;
      elements.verdictValue.style.color = '';
      elements.confidenceBadge.style.color = '';
      elements.confidenceBadge.style.background = '';

      let verdictIcon = '◎';
      if (v.includes("SUPPORTED") && !v.includes("PARTIALLY")) {
        verdictIcon = '✓';
      } else if (v.includes("PARTIALLY")) {
        verdictIcon = '⊘';
      } else if (v.includes("CONTRADICTED")) {
        verdictIcon = '✕';
      }
      elements.verdictValue.innerHTML = `<span style="opacity: 0.7;">${verdictIcon}</span> ${rawVerdict}`;

      if (data._from_cache) {
          elements.verdictBanner.insertAdjacentHTML('beforeend',
              '<div style="font-size:0.75rem; color: var(--text-muted); ' +
              'margin-top: 0.5rem; opacity: 0.6;">⚡ Retrieved from cache</div>'
          );
      }

      // Breakdown
      elements.fullReasoning.textContent = vdata.full_reasoning || "No reasoning provided.";
      elements.whatIsTrue.textContent = vdata.what_is_true || "N/A";
      elements.whatIsFalse.textContent = vdata.what_is_false || "N/A";
      elements.whatIsUnclear.textContent = vdata.what_is_unclear || "N/A";

      // Hidden Stories
      elements.hiddenStoriesContainer.innerHTML = "";
      document.getElementById('hiddenStoriesCount').textContent = Array.isArray(data.hidden_stories) ? data.hidden_stories.length : 0;
      
      if (data.hidden_stories && Array.isArray(data.hidden_stories) && data.hidden_stories.length > 0) {
        data.hidden_stories.forEach(hs => {
          const title = hs.title || "Untitled Story";
          const explanation = hs.explanation || "No explanation available.";
          const significance = hs.significance || "Unknown significance.";
          const hintSources = Array.isArray(hs.which_sources_hint_at_this)
            ? hs.which_sources_hint_at_this.map(s => `<div style="margin-bottom: 0.25rem;">${s}</div>`).join("")
            : "None identified";
          const suppressSources = Array.isArray(hs.which_sources_suppress_this)
            ? hs.which_sources_suppress_this.map(s => `<div style="margin-bottom: 0.25rem;">${s}</div>`).join("")
            : "None identified";
          
          elements.hiddenStoriesContainer.innerHTML += `
            <div class="accordion-item">
              <div class="accordion-header" onclick="toggleAccordion(this)">
                <span>
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:0.5rem; vertical-align: middle;"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>
                  ${title}
                </span>
                <svg class="chevron-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </div>
              <div class="accordion-content">
                <p style="margin-top: 1rem;">${explanation}</p>
                <div class="why-it-matters">
                  <div class="why-it-matters-label">WHY IT MATTERS</div>
                  <p>${significance}</p>
                </div>
                <div class="hidden-story-sources" style="display: flex; gap: 3rem; font-size: 0.9rem; margin-top: 1.5rem; border-top: 1px solid var(--panel-border); padding-top: 1.5rem;">
                  <div style="flex: 1;">
                    <strong style="font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-main); display: block; margin-bottom: 0.75rem;">SOURCES HINTING AT THIS</strong>
                    <div style="color: var(--text-muted);">${hintSources}</div>
                  </div>
                  <div style="flex: 1;">
                    <strong style="font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-main); display: block; margin-bottom: 0.75rem;">SOURCES SUPPRESSING THIS</strong>
                    <div style="color: var(--text-muted);">${suppressSources}</div>
                  </div>
                </div>
              </div>
            </div>
          `;
        });
      } else {
        elements.hiddenStoriesContainer.innerHTML = "<p style='color: var(--text-muted);'>No hidden narratives extracted.</p>";
      }

      // Sources Table
      // ── Split sources into two groups ────────────────────────────────
      const RELEVANT_STANCES = new Set(["SUPPORTS", "CONTRADICTS", "PARTIALLY_SUPPORTS"]);
      const relevantSources = (data.source_analyses || []).filter(
          sa => RELEVANT_STANCES.has(sa.stance)
      );
      const backgroundSources = (data.source_analyses || []).filter(
          sa => !RELEVANT_STANCES.has(sa.stance)
      );

      // ── Update counts in panel header ────────────────────────────────
      document.getElementById("totalCount").textContent =
          (data.source_analyses || []).length;
      document.getElementById("backgroundCount").textContent =
          backgroundSources.length;

      // ── Low-evidence warning ──────────────────────────────────────────
      const warningEl = document.getElementById("lowEvidenceWarning");
      if (relevantSources.length === 0) {
          warningEl.innerHTML = "⚠️ <strong>Limited direct evidence</strong><br>No sources were found which confirm or deny this claim.";
          warningEl.style.display = "block";
      } else if (relevantSources.length < 3) {
          warningEl.innerHTML = "⚠️ <strong>Limited direct evidence</strong><br>Very Few sources were found which directly confirm or deny this claim.";
          warningEl.style.display = "block";
      } else {
          warningEl.style.display = "none";
      }

      // ── Render relevant sources table ─────────────────────────────────
      const relevantBody = document.getElementById("relevantSourcesBody");
      relevantBody.innerHTML = "";
      const noRelevantMsg = document.getElementById("noRelevantMsg");

      if (relevantSources.length === 0) {
          noRelevantMsg.style.display = "block";
      } else {
          noRelevantMsg.style.display = "none";
          relevantSources.forEach(sa => {
              relevantBody.innerHTML += buildSourceRow(sa);
          });
      }

      // ── Render background sources table ───────────────────────────────
      const backgroundBody = document.getElementById("backgroundSourcesBody");
      backgroundBody.innerHTML = "";
      backgroundSources.forEach(sa => {
          backgroundBody.innerHTML += buildSourceRow(sa);
      });

      // ── Hide background accordion entirely if nothing to show ─────────
      const bgSection = document.getElementById("backgroundSourcesSection");
      bgSection.style.display = backgroundSources.length > 0 ? "block" : "none";
      } catch (err) {
        showErrorPanel("Error rendering dashboard: " + err.message);
        console.error(err);
      }
    }

    const authToggleBtn = document.getElementById("authToggleBtn");
    if (authToggleBtn) {
        const token = localStorage.getItem("token") || sessionStorage.getItem("tm_token");
        if (token) {
            authToggleBtn.textContent = "Sign Out";
            authToggleBtn.classList.add("logged-in");
            authToggleBtn.href = "#";

            fetch("/api/validate", { headers: { "Authorization": "Bearer " + token } })
                .then(res => {
                    if (!res.ok) {
                        localStorage.removeItem("token");
                        sessionStorage.removeItem("tm_token");
                        authToggleBtn.textContent = "Sign Up";
                        authToggleBtn.classList.remove("logged-in");
                        authToggleBtn.href = "/static/login.html";
                    }
                }).catch(console.error);

            authToggleBtn.addEventListener("click", (e) => {
                if (authToggleBtn.textContent === "Sign Out") {
                    e.preventDefault();
                    localStorage.removeItem("token");
                    sessionStorage.removeItem("tm_token");
                    window.location.href = "/static/landing.html";
                }
            });
        } else {
            authToggleBtn.textContent = "Sign Up";
            authToggleBtn.classList.remove("logged-in");
            authToggleBtn.href = "/static/login.html";
        }
    }

    // ── Auto-run query parameter handling from Landing Page ──
    const autoClaim = urlParams.get("claim");
    const isCachedQuery = urlParams.get("is_cached") === "1";

    if (autoClaim && autoClaim.trim()) {
      const claimText = autoClaim.trim();
      const claimInput = document.getElementById("claimInput") || elements.claimInput;
      if (claimInput) {
        claimInput.value = claimText;
      }
      if (isCachedQuery) {
        window._tm_bypass_guest_check = true;
        updateGuestClaimGate();
      }

      const token = sessionStorage.getItem("tm_token") || localStorage.getItem("token");
      const isGuest = !token;
      const canRun = !isGuest || isCachedQuery || localStorage.getItem("tm_guest_claim_used") !== "1";

      if (canRun) {
        setTimeout(() => {
          verifyClaim();
        }, 350);
      }
    }
});
  