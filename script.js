// script.js - frontend logic. Every group/stat shown on the page is loaded
// from the Flask API using fetch(). Nothing is hardcoded in the HTML.

// ---------- Small helpers ----------
function $(id) { return document.getElementById(id); }

// Escape text so user input can never inject HTML into the page
function esc(text) {
  const div = document.createElement("div");
  div.textContent = String(text);
  return div.innerHTML;
}

function toast(message, isError) {
  const box = document.createElement("div");
  box.className = "toast" + (isError ? " bad" : "");
  box.textContent = message;
  $("toastBox").appendChild(box);
  setTimeout(function () { box.remove(); }, 4000);
}

// Wrapper around fetch(): returns {ok, status, data}
async function api(url, options) {
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    return { ok: response.ok, status: response.status, data: data };
  } catch (error) {
    return { ok: false, status: 0, data: { message: "Cannot reach the server. Is Flask running?" } };
  }
}

function postJSON(url, body) {
  return api(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}

function formatTime(time24) {
  const parts = time24.split(":");
  let hour = parseInt(parts[0], 10);
  const suffix = hour >= 12 ? "PM" : "AM";
  hour = hour % 12 === 0 ? 12 : hour % 12;
  return hour + ":" + parts[1] + " " + suffix;
}

// ---------- Page navigation (one HTML page, several sections) ----------
const pages = ["home", "explore", "create", "my-groups", "analytics"];

function showPage(name) {
  if (!pages.includes(name)) { name = "home"; }
  pages.forEach(function (p) { $("page-" + p).classList.toggle("active", p === name); });
  document.querySelectorAll("[data-page]").forEach(function (link) {
    link.classList.toggle("active", link.dataset.page === name);
  });
  $("navLinks").classList.remove("open");
  window.scrollTo(0, 0);

  if (name === "home") { loadHome(); }
  if (name === "explore") { loadGroups(); }
  if (name === "analytics") { loadAnalytics(); }
  if (name === "my-groups") { autoLoadMyGroups(); }
}

window.addEventListener("hashchange", function () { showPage(location.hash.slice(1)); });

// ---------- Group card ----------
function groupCard(g, showRole) {
  const percent = Math.round((g.member_count / g.max_members) * 100);
  const topics = g.topics.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("");
  const modeClass = g.mode === "Online" ? "online" : "";
  let bottom = "";

  if (showRole) {
    const names = g.members.map(function (m) { return esc(m.name); }).join(", ");
    bottom = '<p class="members-list"><b>Members:</b> ' + names + "</p>";
    if (g.my_role !== "Creator") {
      bottom += '<button class="btn btn-outline btn-sm" data-leave="' + g.id + '" data-name="' + esc(g.name) + '">Leave Group</button>';
    }
    if (g.my_role === "Creator") {
      bottom += '<button class="btn btn-primary btn-sm" data-edit="' + g.id + '">Edit Group</button>';
      bottom += '<button class="btn btn-danger btn-sm" data-delete="' + g.id + '" data-name="' + esc(g.name) + '">Delete Group</button>';
    }
  } else if (g.status === "Full") {
    bottom = '<button class="btn btn-outline" disabled>Group Full</button>';
  } else {
    bottom = '<button class="btn btn-primary" data-join="' + g.id + '">Join Group</button>';
  }

  return '<article class="group-card">' +
    '<div class="card-top"><span class="badge">' + esc(g.subject) + "</span>" +
    '<span class="badge ' + modeClass + '">' + esc(g.mode) + "</span></div>" +
    "<h3>" + esc(g.name) + "</h3>" +
    '<p class="desc">' + esc(g.description) + "</p>" +
    '<div class="tags">' + topics + "</div>" +
    '<div class="meta"><div><span>Study days</span><br>' + esc(g.day_type) + "</div>" +
    "<div><span>Time</span><br>" + formatTime(g.time) + " (" + esc(g.timing) + ")</div></div>" +
    '<div class="progress"><div style="width:' + percent + '%"></div></div>' +
    '<div class="seats"><span>' + g.member_count + " of " + g.max_members + " members</span>" +
    '<span class="badge ' + g.status.toLowerCase() + '">' + (showRole ? esc(g.my_role) + " · " : "") + g.status + "</span></div>" +
    bottom + "</article>";
}

function emptyBox(message) {
  return '<div class="empty">' + esc(message) + "</div>";
}

// Open the join window when any "Join Group" button is clicked
document.addEventListener("click", function (event) {
  const id = event.target.getAttribute && event.target.getAttribute("data-join");
  if (id) { openJoin(parseInt(id, 10)); }

  const delId = event.target.getAttribute && event.target.getAttribute("data-delete");
  if (delId) { deleteGroup(parseInt(delId, 10), event.target.getAttribute("data-name")); }

  const editId = event.target.getAttribute && event.target.getAttribute("data-edit");
  if (editId) { openEdit(parseInt(editId, 10)); }

  const leaveId = event.target.getAttribute && event.target.getAttribute("data-leave");
  if (leaveId) { leaveGroup(parseInt(leaveId, 10), event.target.getAttribute("data-name")); }
});

// Edit a group (only the creator can; the server checks the email)
async function openEdit(groupId) {
  const result = await api("/api/groups/" + groupId);
  if (!result.ok) { toast(result.data.message, true); return; }
  const g = result.data.group;
  const form = $("editForm");
  clearErrors(form);
  form.elements["group_id"].value = g.id;
  ["name", "subject", "mode", "description", "day_type", "time", "max_members"].forEach(function (field) {
    form.elements[field].value = g[field];
  });
  form.elements["topics"].value = g.topics.join(", ");
  $("editModal").hidden = false;
}

function closeEdit() { $("editModal").hidden = true; }
$("editClose").addEventListener("click", closeEdit);
$("editModal").addEventListener("click", function (e) { if (e.target === $("editModal")) { closeEdit(); } });

$("editForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const form = event.target;
  clearErrors(form);
  const body = Object.fromEntries(new FormData(form).entries());
  const groupId = body.group_id;
  delete body.group_id;
  body.email = $("myEmail").value.trim().toLowerCase();       // proves who the creator is

  const result = await api("/api/groups/" + groupId, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (result.ok) {
    toast(result.data.message);
    closeEdit();
    loadMyGroups(body.email);
  } else {
    if (result.data.errors) { showErrors(form, result.data.errors); }
    toast(result.data.message || "Could not update the group.", true);
  }
});

// Leave a group you joined (the creator can only delete, not leave)
async function leaveGroup(groupId, groupName) {
  if (!confirm('Leave "' + groupName + '"?')) { return; }
  const email = $("myEmail").value.trim().toLowerCase();
  const result = await postJSON("/api/groups/" + groupId + "/leave", { email: email });
  toast(result.data.message, !result.ok);
  if (result.ok) { loadMyGroups(email); }
}

// Delete a group (only the creator can; the server checks the email)
async function deleteGroup(groupId, groupName) {
  if (!confirm('Delete "' + groupName + '"? All its registrations will be removed.')) { return; }
  const email = $("myEmail").value.trim().toLowerCase();
  const result = await api("/api/groups/" + groupId, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email })
  });
  toast(result.data.message, !result.ok);
  if (result.ok) { loadMyGroups(email); }
}

// ---------- A. Home ----------
async function loadHome() {
  const result = await api("/api/groups?available=true");
  if (!result.ok) { $("featuredGrid").innerHTML = emptyBox(result.data.message); return; }
  const groups = result.data.groups.slice(0, 3);
  $("featuredGrid").innerHTML = groups.length ? groups.map(function (g) { return groupCard(g, false); }).join("")
    : emptyBox("No open groups yet. Be the first to create one!");

  const stats = await api("/api/analytics");
  if (stats.ok) {
    $("heroGroups").textContent = stats.data.stats.total_groups;
    $("heroStudents").textContent = stats.data.stats.total_students;
    $("heroSeats").textContent = stats.data.stats.available_seats;
  }
}

// ---------- B. Explore ----------
async function loadGroups() {
  const params = new URLSearchParams();
  if ($("searchInput").value.trim()) { params.set("search", $("searchInput").value.trim()); }
  if ($("filterSubject").value) { params.set("subject", $("filterSubject").value); }
  if ($("filterMode").value) { params.set("mode", $("filterMode").value); }
  if ($("filterTiming").value) { params.set("timing", $("filterTiming").value); }

  const result = await api("/api/groups?" + params.toString());
  if (!result.ok) { $("groupsGrid").innerHTML = emptyBox(result.data.message); return; }

  const groups = result.data.groups;
  $("resultCount").textContent = groups.length + " group" + (groups.length === 1 ? "" : "s") + " found";
  $("groupsGrid").innerHTML = groups.length ? groups.map(function (g) { return groupCard(g, false); }).join("")
    : emptyBox("No groups match your search. Try different filters or create a new group.");
}

let searchTimer = null;
$("searchInput").addEventListener("input", function () {
  clearTimeout(searchTimer);                       // wait until the user stops typing
  searchTimer = setTimeout(loadGroups, 300);
});
["filterSubject", "filterMode", "filterTiming"].forEach(function (id) {
  $(id).addEventListener("change", loadGroups);
});
$("clearFilters").addEventListener("click", function () {
  $("searchInput").value = "";
  ["filterSubject", "filterMode", "filterTiming"].forEach(function (id) { $(id).value = ""; });
  loadGroups();
});

// Fill dropdowns from the API
async function loadOptions() {
  const result = await api("/api/subjects");
  if (!result.ok) { return; }
  const d = result.data;
  d.subjects.forEach(function (s) {
    $("filterSubject").insertAdjacentHTML("beforeend", '<option value="' + esc(s) + '">' + esc(s) + "</option>");
    $("createSubject").insertAdjacentHTML("beforeend", '<option value="' + esc(s) + '">' + esc(s) + "</option>");
    $("editSubject").insertAdjacentHTML("beforeend", '<option value="' + esc(s) + '">' + esc(s) + "</option>");
  });
  d.day_types.forEach(function (t) {
    $("createDayType").insertAdjacentHTML("beforeend", '<option value="' + esc(t) + '">' + esc(t) + "</option>");
    $("editDayType").insertAdjacentHTML("beforeend", '<option value="' + esc(t) + '">' + esc(t) + "</option>");
  });
  d.modes.forEach(function (m) {
    $("filterMode").insertAdjacentHTML("beforeend", '<option value="' + m + '">' + m + "</option>");
  });
  d.timings.forEach(function (t) {
    $("filterTiming").insertAdjacentHTML("beforeend", '<option value="' + t + '">' + t + "</option>");
  });
}

// ---------- Form error helpers ----------
function clearErrors(form) {
  form.querySelectorAll(".error").forEach(function (el) { el.textContent = ""; });
  form.querySelectorAll(".invalid").forEach(function (el) { el.classList.remove("invalid"); });
}

function showErrors(form, errors) {
  Object.keys(errors).forEach(function (field) {
    const box = form.querySelector('[data-error="' + field + '"]');
    if (box) { box.textContent = errors[field]; }
    const input = form.querySelector('[name="' + field + '"]');
    if (input) { input.classList.add("invalid"); }
  });
}

// ---------- C. Create group ----------
$("createForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const form = event.target;
  clearErrors(form);
  const button = form.querySelector("button[type=submit]");
  button.disabled = true;

  const body = Object.fromEntries(new FormData(form).entries());   // form -> object
  const result = await postJSON("/api/groups", body);
  button.disabled = false;

  if (result.ok) {
    toast(result.data.message);
    localStorage.setItem("studymateEmail", body.creator_email);
    form.reset();
    location.hash = "#explore";      // triggers showPage("explore")
  } else {
    if (result.data.errors) { showErrors(form, result.data.errors); }
    toast(result.data.message || "Something went wrong.", true);
  }
});

// ---------- D. Join group ----------
async function openJoin(groupId) {
  const result = await api("/api/groups?available=true");
  const select = $("joinGroupSelect");
  select.innerHTML = "";
  if (!result.ok || result.data.groups.length === 0) {
    toast("No groups with free seats are available right now.", true);
    return;
  }
  result.data.groups.forEach(function (g) {
    select.insertAdjacentHTML("beforeend", '<option value="' + g.id + '">' + esc(g.name) + " (" + g.seats_left + " seats left)</option>");
  });
  if (groupId) { select.value = String(groupId); }
  const saved = localStorage.getItem("studymateEmail");
  if (saved) { $("joinForm").elements["email"].value = saved; }
  clearErrors($("joinForm"));
  $("joinModal").hidden = false;
}

function closeJoin() { $("joinModal").hidden = true; }

$("navJoinBtn").addEventListener("click", function () { openJoin(null); });
$("joinClose").addEventListener("click", closeJoin);
$("joinModal").addEventListener("click", function (e) { if (e.target === $("joinModal")) { closeJoin(); } });

$("joinForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const form = event.target;
  clearErrors(form);
  const groupId = $("joinGroupSelect").value;
  const body = { name: form.elements["name"].value, email: form.elements["email"].value };

  const result = await postJSON("/api/groups/" + groupId + "/join", body);
  if (result.ok) {
    toast(result.data.message);
    localStorage.setItem("studymateEmail", body.email.trim().toLowerCase());
    form.reset();
    closeJoin();
    showPage(location.hash.slice(1));      // refresh whichever page is open
  } else {
    if (result.data.errors) { showErrors(form, result.data.errors); }
    toast(result.data.message || "Could not join the group.", true);
  }
});

// ---------- E. My groups ----------
async function loadMyGroups(email) {
  const result = await api("/api/my-groups?email=" + encodeURIComponent(email));
  if (!result.ok) { $("myGrid").innerHTML = emptyBox(result.data.message); return; }
  const groups = result.data.groups;
  $("myGrid").innerHTML = groups.length ? groups.map(function (g) { return groupCard(g, true); }).join("")
    : emptyBox("No groups found for " + email + ". Join or create one!");
}

function autoLoadMyGroups() {
  const saved = localStorage.getItem("studymateEmail");
  if (saved) { $("myEmail").value = saved; loadMyGroups(saved); }
}

$("myForm").addEventListener("submit", function (event) {
  event.preventDefault();
  const email = $("myEmail").value.trim().toLowerCase();
  localStorage.setItem("studymateEmail", email);
  loadMyGroups(email);
});

// ---------- F. Analytics ----------
async function loadAnalytics() {
  const result = await api("/api/analytics");
  if (!result.ok) { toast("Could not load analytics.", true); return; }
  const s = result.data.stats;

  const cards = [
    ["Total study groups", s.total_groups], ["Registered students", s.total_students],
    ["Total capacity", s.total_capacity], ["Seats available", s.available_seats],
    ["Capacity filled", s.fill_percent + "%"], ["Online / Offline", s.mode_counts.Online + " / " + s.mode_counts.Offline]
  ];
  $("statGrid").innerHTML = cards.map(function (c) {
    return '<div class="stat-card"><strong>' + c[1] + "</strong><span>" + c[0] + "</span></div>";
  }).join("");

  $("popularList").innerHTML = s.popular_subjects.length
    ? s.popular_subjects.map(function (p) {
        return "<li><b>" + esc(p.subject) + "</b> <span>" + p.groups + " group(s), " + p.members + " members</span></li>";
      }).join("")
    : "<li>No data yet</li>";

  // "?t=" makes the browser fetch a fresh chart every time
  const stamp = "?t=" + Date.now();
  $("chartSubjects").src = "/api/analytics/chart/subjects" + stamp;
  $("chartMode").src = "/api/analytics/chart/mode" + stamp;
  $("chartRegs").src = "/api/analytics/chart/registrations" + stamp;
}

// ---------- Mobile menu + start ----------
$("menuToggle").addEventListener("click", function () { $("navLinks").classList.toggle("open"); });
document.querySelectorAll("[data-page]").forEach(function (link) {
  link.addEventListener("click", function () { $("navLinks").classList.remove("open"); });
});

loadOptions();
showPage(location.hash.slice(1) || "home");
