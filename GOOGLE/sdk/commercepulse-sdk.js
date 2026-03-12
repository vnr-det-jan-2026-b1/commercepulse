/**
 * CommercePulse++ Event Collection SDK
 * Lightweight browser SDK for tracking seller storefront events.
 *
 * Usage:
 *   <script src="https://cdn.commercepulse.app/sdk/v1/cp-sdk.min.js"
 *           data-cp-seller="seller-001"
 *           data-cp-marketplace="flipkart"
 *           data-cp-endpoint="https://collector.commercepulse.app">
 *   </script>
 */
(function (window) {
  "use strict";

  const script     = document.currentScript;
  const sellerId   = script?.getAttribute("data-cp-seller")      || "";
  const marketplace= script?.getAttribute("data-cp-marketplace") || "unknown";
  const endpoint   = script?.getAttribute("data-cp-endpoint")    || "https://collector.commercepulse.app";
  const signingKey = script?.getAttribute("data-cp-key")         || "";

  if (!sellerId) {
    console.warn("[CommercePulse] Missing data-cp-seller attribute. Tracking disabled.");
    return;
  }

  // ── Utilities ──────────────────────────────────────────────

  function getOrCreateSessionId() {
    let sid = sessionStorage.getItem("cp_session");
    if (!sid) {
      sid = "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      sessionStorage.setItem("cp_session", sid);
    }
    return sid;
  }

  function getAnonymousId() {
    let aid = localStorage.getItem("cp_anon");
    if (!aid) {
      aid = "a-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem("cp_anon", aid);
    }
    return aid;
  }

  function getUtmParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      utm_source:   params.get("utm_source")   || "",
      utm_medium:   params.get("utm_medium")   || "",
      utm_campaign: params.get("utm_campaign") || "",
    };
  }

  function getDeviceType() {
    const ua = navigator.userAgent;
    if (/tablet|ipad/i.test(ua))                return "tablet";
    if (/mobile|android|iphone/i.test(ua))      return "mobile";
    return "desktop";
  }

  // ── Core send function ─────────────────────────────────────

  const queue = [];
  let flushing = false;

  function send(eventType, extra) {
    const event = {
      event_id:     crypto.randomUUID ? crypto.randomUUID()
                    : Math.random().toString(36).slice(2),
      seller_id:    sellerId,
      session_id:   getOrCreateSessionId(),
      anonymous_id: getAnonymousId(),
      event_type:   eventType,
      marketplace:  marketplace,
      timestamp:    Date.now(),
      page_url:     window.location.href.slice(0, 512),
      referrer:     document.referrer.slice(0, 512),
      device_type:  getDeviceType(),
      ...getUtmParams(),
      ...extra,
    };

    queue.push(event);
    if (!flushing) flush();
  }

  function flush() {
    if (queue.length === 0) { flushing = false; return; }
    flushing = true;
    const batch = queue.splice(0, 25);

    const body = JSON.stringify({ seller_id: sellerId, events: batch });

    fetch(`${endpoint}/collect/batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {
      // Silently fail — don't impact seller storefront
    }).finally(() => {
      setTimeout(flush, 250);
    });
  }

  // ── Auto-tracking ──────────────────────────────────────────

  // page_view on load
  window.addEventListener("DOMContentLoaded", function () {
    send("page_view", {});
  });

  // product_view — detect elements with data-cp-sku
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        const el  = entry.target;
        const sku = el.getAttribute("data-cp-sku");
        if (sku) {
          send("product_view", { product_sku: sku });
          observer.unobserve(el);   // fire once per product per session
        }
      }
    });
  }, { threshold: 0.5 });

  document.querySelectorAll("[data-cp-sku]").forEach(function (el) {
    observer.observe(el);
  });

  // add_to_cart, checkout_start, purchase — button clicks
  document.addEventListener("click", function (e) {
    const el = e.target.closest("[data-cp-event]");
    if (!el) return;
    const eventType = el.getAttribute("data-cp-event");
    const sku       = el.getAttribute("data-cp-sku") || "";
    if (["add_to_cart", "checkout_start", "checkout_complete", "purchase"].includes(eventType)) {
      send(eventType, { product_sku: sku });
    }
  });

  // ── Public API ─────────────────────────────────────────────

  window.CommercePulse = {
    track: send,
    identify: function (userId) {
      localStorage.setItem("cp_user", userId);
    },
  };

})(window);
