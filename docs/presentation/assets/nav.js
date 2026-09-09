var pages = [
  { file: "index.html", label: "Start", title: "Scaling AI in Real Software", kicker: "Start" },
  { file: "01-problem.html", label: "Drift", title: "The Problem - Three Kinds of Drift", kicker: "The Problem" },
  { file: "02-context-tax.html", label: "Context Tax", title: "The Cost - The Daily Context Tax", kicker: "The Cost" },
  { file: "03-bottleneck.html", label: "Bottleneck", title: "The Bottleneck Moved", kicker: "The Bottleneck" },
  { file: "04-agile-inversion.html", label: "Balance", title: "The Balance - AI and Agile", kicker: "The Balance" },
  { file: "05-modes.html", label: "Modes", title: "The Choice - Two Operating Modes", kicker: "The Choice" },
  { file: "06-four-artifacts.html", label: "4 Files", title: "The Practice - Four Committed Files", kicker: "The Practice" },
  { file: "07-colocation.html", label: "Co-location", title: "Architecture - Co-location and Hierarchy", kicker: "Architecture" },
  { file: "08-roles.html", label: "Roles", title: "Governance - Human Navigator, AI Driver", kicker: "Governance" },
  { file: "09-lifecycle.html", label: "Lifecycle", title: "Delivery Flow - From Aim to Merge", kicker: "Delivery Flow" },
  { file: "10-payoff.html", label: "Payoff", title: "The Payoff - ROI and 4-Phase Adoption", kicker: "The Payoff" }
];

var currentFile = window.location.pathname.split("/").pop() || "index.html";
var isManifesto = currentFile === "ai-agile-manifesto.html";
var currentIndex = pages.findIndex(function (page) { return page.file === currentFile; });
if (currentIndex === -1 && !isManifesto) currentIndex = 0;

// With more pages than fit the header width, the topnav list scrolls
// horizontally. Center the active page so it isn't hidden off-screen.
function centerActiveNavLink(nav) {
  var activeLink = nav.querySelector('a[aria-current="page"]');
  if (!activeLink) return;
  var navRect = nav.getBoundingClientRect();
  var linkRect = activeLink.getBoundingClientRect();
  var offset = (linkRect.left - navRect.left) - (nav.clientWidth - linkRect.width) / 2;
  var maxScroll = nav.scrollWidth - nav.clientWidth;
  nav.scrollLeft = Math.max(0, Math.min(nav.scrollLeft + offset, maxScroll));
}

document.querySelectorAll(".topnav").forEach(function (nav) {
  nav.innerHTML = pages.map(function (page, index) {
    var current = index === currentIndex ? ' aria-current="page"' : "";
    return '<a href="' + page.file + '"' + current + '><span class="nav-num">' +
      String(index + 1).padStart(2, "0") + "</span> " + page.label + "</a>";
  }).join("");

  centerActiveNavLink(nav);
});

// Layout can still settle after stylesheets/images finish loading, so
// re-center once everything is done, and again if the viewport is resized.
window.addEventListener("load", function () {
  document.querySelectorAll(".topnav").forEach(centerActiveNavLink);
});
var resizeTimer;
window.addEventListener("resize", function () {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(function () {
    document.querySelectorAll(".topnav").forEach(centerActiveNavLink);
  }, 150);
});

// Keep this reading route outside the numbered, horizontally scrolling guide.
document.querySelectorAll(".topbar").forEach(function (topbar) {
  var utility = topbar.querySelector(".utility-nav");
  if (!utility) {
    utility = document.createElement("nav");
    utility.className = "utility-nav";
    utility.setAttribute("aria-label", "Manifesto");
    topbar.appendChild(utility);
  }
  utility.innerHTML = '<a href="ai-agile-manifesto.html"' +
    (isManifesto ? ' aria-current="page"' : "") + '>Manifesto</a>';
});

function setPageLink(link, page, prefix) {
  if (!link || !page) return;
  link.href = page.file;
  var metadata = link.querySelector(".page-nav-meta");
  if (metadata) metadata.textContent = prefix + " - Page " + (pages.indexOf(page) + 1);
  var title = link.querySelector("div > span:last-child");
  if (title) title.textContent = page.title;
}

// The manifesto retains its static heading, footer, and ordinary reading links.
if (!isManifesto) {
  var kicker = document.querySelector(".kicker");
  if (kicker) kicker.textContent = pages[currentIndex].kicker + " - " + (currentIndex + 1) + " / " + pages.length;

  document.querySelectorAll(".site-footer > span:first-child").forEach(function (footer) {
    footer.textContent = "saiga-cart Guide - Page " + (currentIndex + 1) + " of " + pages.length;
  });

  setPageLink(document.querySelector(".page-nav .prev"), pages[currentIndex - 1], "Previous");
  setPageLink(document.querySelector(".page-nav .next"), pages[currentIndex + 1], "Next");

  document.documentElement.dataset.keyboardNav = "ready";
  document.addEventListener("keydown", function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    var tagName = event.target && event.target.tagName;
    if (tagName && /^(INPUT|TEXTAREA|SELECT)$/.test(tagName)) return;

    var destination = null;
    if (event.key === "ArrowLeft") destination = document.querySelector(".page-nav .prev");
    if (event.key === "ArrowRight") destination = document.querySelector(".page-nav .next");
    if (destination && destination.href) window.location.href = destination.href;
  });
}
