# Aurora — Autoconhecimento

## Sobre o projeto

Aurora é uma plataforma de autoconhecimento que transforma a numerologia em uma experiência de escuta, reflexão e escolha consciente.

Seu propósito é oferecer mapas numerológicos personalizados a partir do nome e da data de nascimento de cada pessoa. O relatório organiza cálculos, símbolos e interpretações em uma leitura acolhedora, profunda e prática — um espelho para reconhecer talentos, desejos, padrões, desafios e possibilidades de evolução.

O site foi pensado para pessoas que desejam olhar para a própria história com mais presença. A numerologia não aparece como uma sentença sobre o futuro, mas como uma porta de entrada para perguntas importantes: o que está pedindo atenção? Quais forças já existem? Onde é possível agir com mais autonomia?

Cada pedido passa por uma revisão antes da entrega. Assim, a tecnologia cuida da organização dos dados e dos cálculos, enquanto a sensibilidade humana preserva o contexto, o tom e a responsabilidade da leitura.

### Finalidade

- oferecer uma experiência sofisticada de autoconhecimento;
- gerar mapas personalizados em PDF;
- apresentar cálculos e interpretações com transparência;
- estimular reflexão sem prometer acontecimentos inevitáveis;
- respeitar a autonomia de cada pessoa;
- desenvolver futuramente conteúdos relacionados ao sagrado feminino.

Aurora é, acima de tudo, um convite para voltar ao centro. O mapa pode indicar caminhos, mas quem escolhe como atravessá-los é sempre a própria pessoa.

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
