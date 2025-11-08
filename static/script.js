// ---------------- REGISTER TEAM ----------------
async function registerTeam() {
  const teamName = document.getElementById("team_name").value.trim();
  const membersInput = document.getElementById("members").value.trim();

  if (!teamName || !membersInput) {
    alert("Please enter both team name and members.");
    return;
  }

  const members = membersInput.split(",").map(m => m.trim());

  try {
    const res = await fetch("/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team_name: teamName, members }),
    });

    const data = await res.json();

    if (data.error) {
      alert("Error: " + data.error);
      return;
    }

    const qrContainer = document.getElementById("qr-container");
    qrContainer.classList.remove("hidden");
    const qrImg = document.getElementById("qr");
    qrImg.src = "data:image/png;base64," + data.qr;
    document.getElementById("download-link").href = qrImg.src;
  } catch (err) {
    console.error(err);
    alert("Could not generate QR. Check console for details.");
  }
}

// ---------------- DASHBOARD SCANNER ----------------
if (window.location.pathname.includes("dashboard")) {
  let html5QrCode = new Html5Qrcode("reader");

  async function onScanSuccess(decodedText) {
    try {
      const qrData = JSON.parse(decodedText);

      const res = await fetch(`/team/${qrData.team_id}`);
      const data = await res.json();

      if (data.error) {
        alert("⚠️ Team not found!");
        return;
      }

      const team = data.team;
      const members = data.members;

      document.getElementById("team-info").classList.remove("hidden");
      document.getElementById("team-name").innerText = `Team: ${team.team_name}`;
      document.getElementById("team-members").innerText =
        `Members: ${JSON.parse(team.members).join(", ")}`;

      const tbody = document.querySelector("#members-table tbody");
      tbody.innerHTML = "";

      members.forEach((m) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${m.member_name}</td>
          <td><input type="checkbox" data-id="${m.member_id}" data-field="check_in" ${m.check_in ? "checked" : ""}></td>
          <td><input type="checkbox" data-id="${m.member_id}" data-field="snacks" ${m.snacks ? "checked" : ""}></td>
          <td><input type="checkbox" data-id="${m.member_id}" data-field="dinner" ${m.dinner ? "checked" : ""}></td>
          <td><input type="checkbox" data-id="${m.member_id}" data-field="check_out" ${m.check_out ? "checked" : ""}></td>
        `;
        tbody.appendChild(row);
      });

      window.currentMembers = members;
      html5QrCode.stop();

      document.getElementById("scan-next").classList.remove("hidden");
    } catch (err) {
      console.error("Invalid QR", err);
      alert("Invalid QR code!");
    }
  }

  html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: 250 }, onScanSuccess)
    .catch(err => alert("Camera error: " + err));

  window.startNextScan = function() {
    document.getElementById("team-info").classList.add("hidden");
    document.getElementById("scan-next").classList.add("hidden");
    html5QrCode = new Html5Qrcode("reader");
    html5QrCode.start({ facingMode: "environment" }, { fps: 10, qrbox: 250 }, onScanSuccess);
  };
}

async function updateMembers() {
  if (!window.currentMembers) {
    alert("No team scanned!");
    return;
  }

  const checkboxes = document.querySelectorAll("#members-table input[type=checkbox]");
  const updates = {};

  checkboxes.forEach(chk => {
    const id = chk.dataset.id;
    const field = chk.dataset.field;
    if (!updates[id]) updates[id] = { member_id: id, check_in: 0, snacks: 0, dinner: 0, check_out: 0 };
    updates[id][field] = chk.checked ? 1 : 0;
  });

  const res = await fetch("/update_members", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ members: Object.values(updates) }),
  });

  const data = await res.json();
  if (data.status === "updated") alert("✅ Member statuses updated!");
}
