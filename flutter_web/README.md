# Casca web do Flutter

O site do debate de 23/10 mora em `web/`. Esta pasta guarda o `index.html`, o manifesto e os ícones que o Flutter espera em `web/` quando for gerar a versão web do aplicativo.

Para uma pré-visualização Flutter no navegador, sem apagar o site:

```bash
mv web /tmp/placar-site
cp -a flutter_web web
flutter run -d web-server --web-port 43123 --web-hostname 0.0.0.0
```

Depois, devolva o site estático:

```bash
rm -rf web
mv /tmp/placar-site web
```
