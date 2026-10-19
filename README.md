# Aurora — Autoconhecimento

Primeira versão funcional do site para pedidos de mapas numerológicos personalizados.

## Executar

```bash
python3 app.py
```

Abra `http://127.0.0.1:8000`. O painel de revisão fica em `/admin?key=demo-admin`.

Para trocar a chave do painel:

```bash
MAPA_ADMIN_KEY='uma-chave-forte' python3 app.py
```

Os pedidos ficam em `data/orders.json` e PDFs aprovados em `data/pdfs/`. Em produção, substituir o armazenamento local, configurar HTTPS, autenticação real, provedor de pagamento e serviço de e-mail.

## Testes

```bash
python3 -m unittest discover -s tests -v
```

# numerologia_sagrada
