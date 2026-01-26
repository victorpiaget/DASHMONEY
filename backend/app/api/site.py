from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index() -> str:
    """
    Page HTML minimale (site V0).
    Elle envoie un POST /net-worth/compute via fetch et affiche le JSON résultat.
    """
    return """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>DASHMONEY - V0</title>
  </head>
  <body>
    <h1>DASHMONEY (V0)</h1>
    <p>Entrez des données JSON puis cliquez sur Calculer.</p>

    <h2>Payload</h2>
    <textarea id="payload" rows="18" cols="90"></textarea>
    <br />
    <button id="btn">Calculer Net Worth</button>

    <h2>Résultat</h2>
    <pre id="result"></pre>

    <script>
      // Exemple par défaut : 2 actifs EUR + 1 dette EUR + 1 actif USD + 1 dette USD
      const defaultPayload = {
        assets: [
          { name: "Compte courant", category: "FINANCIAL", value: { amount: 5000, currency: "EUR" } },
          { name: "Livret A", category: "FINANCIER", value: { amount: 10000, currency: "EUR" } },
          { name: "Compte USD", category: "FINANCIAL", value: { amount: 2000, currency: "USD" } }
        ],
        liabilities: [
          { name: "Crédit auto", balance: { amount: 3000, currency: "EUR" } },
          { name: "Dette USD", balance: { amount: 3000, currency: "USD" } }
        ]
      };

      document.getElementById("payload").value = JSON.stringify(defaultPayload, null, 2);

      document.getElementById("btn").addEventListener("click", async () => {
        const resultEl = document.getElementById("result");
        resultEl.textContent = "Calcul en cours...";

        let payload;
        try {
          payload = JSON.parse(document.getElementById("payload").value);
        } catch (e) {
          resultEl.textContent = "JSON invalide : " + e;
          return;
        }

        try {
          const res = await fetch("/net-worth/compute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });

          const text = await res.text();
          if (!res.ok) {
            resultEl.textContent = "Erreur API (" + res.status + "):\\n" + text;
            return;
          }

          // Affiche le JSON formaté
          resultEl.textContent = JSON.stringify(JSON.parse(text), null, 2);

        } catch (e) {
          resultEl.textContent = "Erreur réseau : " + e;
        }
      });
    </script>
  </body>
</html>
"""
