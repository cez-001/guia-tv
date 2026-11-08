# Guia TV

Programação de TV na ordem dos teus canais. App web instalável no telemóvel.

## Pôr a funcionar
1. No GitHub: **New repository** (pode ser privado ou público; para o Pages gratuito, público).
2. Carrega **todo o conteúdo desta pasta** para o repositório (inclui a pasta oculta `.github`).
3. **Settings → Actions → General → Workflow permissions →** "Read and write permissions" → Save.
4. **Actions → Atualizar programação → Run workflow.** Espera 1–3 minutos; deve aparecer um commit novo em `data/epg.json`.
5. **Settings → Pages →** Source: "Deploy from a branch", Branch: `main`, pasta `/ (root)` → Save.
6. Abre o endereço que o GitHub indicar (algo como `https://O-TEU-NOME.github.io/NOME-DO-REPO/`).
7. No iPhone: Partilhar → "Adicionar ao ecrã principal".

Depois, em "Os meus canais", cola a tua lista (um canal por linha) ou escolhe à mão. A ordem fica guardada no teu telemóvel.

A programação atualiza sozinha às 5h e às 17h (UTC).

## Se a ação falhar
Copia o erro do passo "Obter programação" e envia-o.
