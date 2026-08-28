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
var currentIndex = pages.findIndex(function (page) { return page.file === currentFile; });
if (currentIndex === -1) currentIndex = 0;

document.querySelectorAll(".topnav").forEach(function (nav) {
  nav.innerHTML = pages.map(function (page, index) {
    var current = index === currentIndex ? ' aria-current="page"' : "";
    return '<a href="' + page.file + '"' + current + '><span class="nav-num">' +
      String(index + 1).padStart(2, "0") + "</span> " + page.label + "</a>";
  }).join("");
});

var kicker = document.querySelector(".kicker");
if (kicker) kicker.textContent = pages[currentIndex].kicker + " - " + (currentIndex + 1) + " / " + pages.length;

document.querySelectorAll(".site-footer > span:first-child").forEach(function (footer) {
  footer.textContent = "saiga-cart Guide - Page " + (currentIndex + 1) + " of " + pages.length;
});

function setPageLink(link, page, prefix) {
  if (!link || !page) return;
  link.href = page.file;
  var metadata = link.querySelector(".page-nav-meta");
  if (metadata) metadata.textContent = prefix + " - Page " + (pages.indexOf(page) + 1);
  var title = link.querySelector("div > span:last-child");
  if (title) title.textContent = page.title;
}

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
