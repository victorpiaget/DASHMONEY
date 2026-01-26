from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])


@router.get("/accounts/{account_id}/transactions-ui", response_class=HTMLResponse)
def account_transactions_ui(account_id: str) -> HTMLResponse:
    # IMPORTANT: on utilise une f-string pour injecter account_id,
    # donc on doit écrire le JS/CSS avec des { } normaux, et les
    # templates JS `${...}` doivent être échappés en `${{...}}` dans une f-string Python.
    html = f"""
<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>DASHMONEY — Transactions</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    h1 {{ margin-bottom: 6px; }}
    .meta {{ color: #555; margin-bottom: 16px; }}
    .row {{ display: flex; gap: 16px; flex-wrap: wrap; align-items: flex-start; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; }}
    label {{ display: block; font-size: 12px; margin-top: 8px; }}
    input, select {{ padding: 8px; min-width: 200px; }}
    button {{ padding: 10px 14px; margin-top: 12px; cursor: pointer; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th, td {{ border-bottom: 1px solid #eee; padding: 8px; text-align: left; }}
    th {{ background: #fafafa; }}
    .neg {{ color: #b00020; }}
    .pos {{ color: #0a7a0a; }}
    .err {{ color: #b00020; white-space: pre-wrap; }}
    .muted {{ color: #777; font-size: 12px; }}
  </style>
</head>

<body>
  <h1>Transactions — <span id="accountTitle">...</span></h1>
  <div class="meta">
    Compte : <b id="accountId">{account_id}</b> — Devise : <b id="accountCurrency">...</b>
  </div>

  <div class="row">
    <div class="card">
      <h3>Ajouter une transaction</h3>

      <label>Date</label>
      <input id="date" type="date" />

      <label>Kind</label>
      <select id="kind">
        <option value="EXPENSE">EXPENSE</option>
        <option value="INCOME">INCOME</option>
        <option value="INVESTMENT">INVESTMENT</option>
        <option value="ADJUSTMENT">ADJUSTMENT</option>
      </select>

      <label>Montant (ex : -12.35 ou 100.00)</label>
      <input id="amount" type="text" placeholder="-12.35" />

      <label>Catégorie</label>
      <input id="category" type="text" placeholder="Transport & mobilité" />

      <label>Sous-catégorie (optionnel)</label>
      <input id="subcategory" type="text" placeholder="Carburant" />

      <label>Label (optionnel)</label>
      <input id="label" type="text" placeholder="Uber" />

      <button id="btnAdd" type="button">Ajouter</button>
      <div class="muted">Après ajout, la table se recharge automatiquement.</div>
      <div id="formError" class="err"></div>
    </div>

    <div class="card" style="flex:1; min-width: 420px;">
      <h3>Tableau</h3>
      <button id="btnRefresh" type="button">Rafraîchir</button>
      <div id="loadError" class="err"></div>

      <section id="filters" style="padding:12px; border:1px solid #ddd; border-radius:8px; margin:12px 0;">
        <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:flex-end;">
          <div>
            <label for="dateFrom">Date from</label><br />
            <input id="dateFrom" type="date" />
          </div>

          <div>
            <label for="dateTo">Date to</label><br />
            <input id="dateTo" type="date" />
          </div>

          <div>
            <label>Kinds</label><br />
            <label><input type="checkbox" class="kindChk" value="INCOME" /> INCOME</label>
            <label><input type="checkbox" class="kindChk" value="EXPENSE" /> EXPENSE</label>
            <label><input type="checkbox" class="kindChk" value="INVESTMENT" /> INVESTMENT</label>
            <label><input type="checkbox" class="kindChk" value="ADJUSTMENT" /> ADJUSTMENT</label>
          </div>

          <div>
            <label for="qLabel">Label contains</label><br />
            <input id="qLabel" type="text" placeholder="ex: uber, total, ..." />
          </div>

          <div>
            <label for="sortBy">Sort by</label><br />
            <select id="sortBy">
              <option value="date">date</option>
              <option value="amount">amount</option>
              <option value="kind">kind</option>
              <option value="category">category</option>
              <option value="subcategory">subcategory</option>
              <option value="label">label</option>
            </select>
          </div>

          <div>
            <label for="sortDir">Dir</label><br />
            <select id="sortDir">
              <option value="asc">asc</option>
              <option value="desc">desc</option>
            </select>
          </div>

          <div style="display:flex; gap:8px;">
            <button id="applyBtn" type="button">Apply</button>
            <button id="resetBtn" type="button">Reset</button>
          </div>

          <div style="margin-left:auto;">
            <strong id="resultCount">0</strong> rows
          </div>
        </div>
      </section>

      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Seq</th>
            <th>Kind</th>
            <th>Catégorie</th>
            <th>Sous-catégorie</th>
            <th>Montant</th>
            <th>Solde après</th>
          </tr>
        </thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>

    <div class="card">
      <h3>Importer un CSV</h3>

      <input id="csvFile" type="file" accept=".csv" />
      <button id="btnImport" type="button">Importer</button>

      <div id="importMsg" class="muted"></div>
      <div id="importErr" class="err"></div>
    </div>
  </div>

<script>
const accountId = "{account_id}";

function fmtSigned(v) {{
  if (v === null || v === undefined) return "";
  const s = String(v);
  return s;
}}

function clsSigned(v) {{
  const n = Number(v);
  if (Number.isNaN(n)) return "";
  return n < 0 ? "neg" : "pos";
}}

async function loadAccountMeta() {{
  const res = await fetch("/accounts");
  if (!res.ok) throw new Error("GET /accounts failed");
  const accounts = await res.json();
  const acc = accounts.find(a => a.id === accountId);
  if (!acc) throw new Error("Compte introuvable : " + accountId);
  document.getElementById("accountTitle").textContent = acc.name;
  document.getElementById("accountCurrency").textContent = acc.currency;
}}

function buildQueryParams() {{
  const params = new URLSearchParams();

  const dateFrom = document.getElementById("dateFrom").value;
  const dateTo = document.getElementById("dateTo").value;
  const qLabel = document.getElementById("qLabel").value.trim();

  if (dateFrom) params.append("date_from", dateFrom);
  if (dateTo) params.append("date_to", dateTo);
  if (qLabel) params.append("q", qLabel);

  document.querySelectorAll(".kindChk").forEach(chk => {{
    if (chk.checked) params.append("kinds", chk.value);
  }});

  params.append("sort_by", document.getElementById("sortBy").value);
  params.append("sort_dir", document.getElementById("sortDir").value);

  return params;
}}

async function loadTable() {{
  const loadErr = document.getElementById("loadError");
  loadErr.textContent = "";

  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";

  const params = buildQueryParams();
  const url = `/accounts/${{encodeURIComponent(accountId)}}/transactions-with-balance?${{params.toString()}}`;

  const res = await fetch(url);
  if (!res.ok) {{
    const txt = await res.text();
    throw new Error("Erreur API : HTTP " + res.status + "\\n" + txt);
  }}

  const rows = await res.json();
  document.getElementById("resultCount").textContent = String(rows.length);

  for (const item of rows) {{
    const tx = item.transaction;
    const balStr = item.balance_after;

    // ton JSON: tx.amount = {{amount: -75.16, currency:"EUR"}}
    const amountNum = tx.amount?.amount;
    const amountCur = tx.amount?.currency || "";
    const amountText = (typeof amountNum === "number") ? amountNum.toFixed(2) + " " + amountCur : fmtSigned(amountNum);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${{tx.date}}</td>
      <td>${{tx.sequence}}</td>
      <td>${{tx.kind}}</td>
      <td>${{tx.category}}</td>
      <td>${{tx.subcategory ?? ""}}</td>
      <td class="${{clsSigned(amountNum)}}">${{amountText}}</td>
      <td class="${{clsSigned(balStr)}}">${{fmtSigned(balStr)}}</td>
    `;
    tbody.appendChild(tr);
  }}
}}

async function addTransaction() {{
  document.getElementById("formError").textContent = "";

  const payload = {{
    date: document.getElementById("date").value,
    kind: document.getElementById("kind").value,
    amount: document.getElementById("amount").value.trim(),
    category: document.getElementById("category").value.trim(),
    subcategory: document.getElementById("subcategory").value.trim() || null,
    label: document.getElementById("label").value.trim() || null,
  }};

  try {{
    const res = await fetch(`/accounts/${{encodeURIComponent(accountId)}}/transactions`, {{
      method: "POST",
      headers: {{ "Content-Type": "application/json" }},
      body: JSON.stringify(payload),
    }});

    if (!res.ok) {{
      const txt = await res.text();
      throw new Error("POST failed: HTTP " + res.status + "\\n" + txt);
    }}

    document.getElementById("amount").value = "";
    document.getElementById("category").value = "";
    document.getElementById("subcategory").value = "";
    document.getElementById("label").value = "";

    await loadTable();
  }} catch (e) {{
    document.getElementById("formError").textContent = String(e);
  }}
}}

document.getElementById("btnRefresh").addEventListener("click", async () => {{
  try {{
    await loadTable();
  }} catch (e) {{
    document.getElementById("loadError").textContent = String(e);
  }}
}});

document.getElementById("btnAdd").addEventListener("click", async () => {{
  await addTransaction();
}});

document.getElementById("applyBtn").addEventListener("click", async () => {{
  try {{
    console.log("Apply clicked", buildQueryParams().toString());
    await loadTable();
  }} catch (e) {{
    document.getElementById("loadError").textContent = String(e);
  }}
}});

document.getElementById("resetBtn").addEventListener("click", async () => {{
  document.getElementById("dateFrom").value = "";
  document.getElementById("dateTo").value = "";
  document.getElementById("qLabel").value = "";
  document.getElementById("sortBy").value = "date";
  document.getElementById("sortDir").value = "asc";
  document.querySelectorAll(".kindChk").forEach(chk => chk.checked = false);

  try {{
    await loadTable();
  }} catch (e) {{
    document.getElementById("loadError").textContent = String(e);
  }}
}});

(async () => {{
  try {{
    await loadAccountMeta();
    await loadTable();
  }} catch (e) {{
    document.getElementById("loadError").textContent = String(e);
  }}
}})();

// Import CSV
document.getElementById("btnImport").addEventListener("click", async () => {{
  document.getElementById("importErr").textContent = "";
  document.getElementById("importMsg").textContent = "";

  const fileInput = document.getElementById("csvFile");
  if (!fileInput.files || fileInput.files.length === 0) {{
    document.getElementById("importErr").textContent = "Choisis un fichier CSV.";
    return;
  }}

  const fd = new FormData();
  fd.append("file", fileInput.files[0]);

  try {{
    const res = await fetch(`/accounts/${{encodeURIComponent(accountId)}}/import-victor`, {{
      method: "POST",
      body: fd,
    }});

    let data = null;
    try {{
      data = await res.json();
    }} catch {{
      const txt = await res.text();
      throw new Error("Réponse non-JSON :\\n" + txt);
    }}

    if (!res.ok) throw new Error(JSON.stringify(data));

    document.getElementById("importMsg").textContent =
      `Import terminé : ${{data.imported}} lignes importées, ${{data.errors_count}} erreurs.`;

    if (data.errors_count > 0) {{
      document.getElementById("importErr").textContent =
        "Erreurs (preview) :\\n" + data.errors_preview.join("\\n");
    }}

    await loadTable();
  }} catch (e) {{
    document.getElementById("importErr").textContent = String(e);
  }}
}});
</script>

</body>
</html>
"""
    return HTMLResponse(html)
