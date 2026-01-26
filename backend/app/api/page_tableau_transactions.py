from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/transactions_ui", response_class=HTMLResponse)
def transactions_ui():
    return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>DASHMONEY – Transactions</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ccc; padding: 6px; text-align: left; }
        th { background: #eee; }
        input, select, button { margin: 4px; }
    </style>
</head>
<body>

<h1>DASHMONEY – Transactions (V0)</h1>

<h2>Ajouter une transaction</h2>

<form id="tx-form">
    <input name="account_id" placeholder="account_id" value="main" required>
    <input type="date" name="date" required>
    <input name="amount" placeholder="amount (ex: -12.34)" required>

    <select name="currency">
        <option value="EUR">EUR</option>
        <option value="USD">USD</option>
    </select>

    <select name="kind">
        <option value="INCOME">INCOME</option>
        <option value="EXPENSE">EXPENSE</option>
        <option value="INVESTMENT">INVESTMENT</option>
        <option value="ADJUSTMENT">ADJUSTMENT</option>
    </select>

    <input name="category" placeholder="category" required>
    <input name="subcategory" placeholder="subcategory">
    <input name="label" placeholder="label">

    <button type="submit">Ajouter</button>
</form>

<h2>Transactions</h2>

<button onclick="loadTransactions()">Rafraîchir</button>

<table>
    <thead>
        <tr>
            <th>Date</th>
            <th>Seq</th>
            <th>Compte</th>
            <th>Montant</th>
            <th>Devise</th>
            <th>Type</th>
            <th>Catégorie</th>
            <th>Sous-cat</th>
            <th>Label</th>
        </tr>
    </thead>
    <tbody id="tx-table"></tbody>
</table>

<script>
async function loadTransactions() {
    const res = await fetch("/transactions");
    const data = await res.json();

    const tbody = document.getElementById("tx-table");
    tbody.innerHTML = "";

    for (const tx of data) {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${tx.date}</td>
            <td>${tx.sequence}</td>
            <td>${tx.account_id}</td>
            <td>${tx.amount}</td>
            <td>${tx.currency}</td>
            <td>${tx.kind}</td>
            <td>${tx.category}</td>
            <td>${tx.subcategory ?? ""}</td>
            <td>${tx.label ?? ""}</td>
        `;
        tbody.appendChild(tr);
    }
}

document.getElementById("tx-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;

    const payload = {
        account_id: form.account_id.value,
        date: form.date.value,
        amount: form.amount.value,
        currency: form.currency.value,
        kind: form.kind.value,
        category: form.category.value,
        subcategory: form.subcategory.value || null,
        label: form.label.value || null,
    };

    const res = await fetch("/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    if (!res.ok) {
        alert("Erreur : " + await res.text());
        return;
    }

    form.amount.value = "";
    form.label.value = "";
    loadTransactions();
});

loadTransactions();
</script>

</body>
</html>
"""
