# Placar da Verdade

Aplicativo Flutter (Android e iOS) do placar ao vivo de um debate, no mesmo espírito do site [Placar da Verdade](https://placar.zenithonacademy.com.br/): Mentirômetro, propostas versus ataques, linha do tempo de 5 minutos e os fatos checados, com a fonte ao lado.

A interface está em português (pt-BR). A checagem automática pode errar — o app repete o aviso do site.

## O que tem na tela

- **Mentirômetro.** O ponteiro pende para quem tem mais afirmações falsas ou imprecisas. Impreciso vale meio ponto. "Sem dados" e "Em revisão" ficam de fora. Com menos de 3 fatos checáveis de cada lado, o ponteiro fica no centro.
- **Propostas ou ataques?** Contagem por candidato e a barra de como cada um usou o tempo de fala (propondo, atacando, se defendendo, falando do passado).
- **Propostas explicadas.** Tela separada, ligada em "Ver as propostas explicadas".
- **Linha do tempo.** Uma coluna a cada 5 minutos. Toque numa coluna para filtrar os fatos daqueles minutos.
- **Fatos checados.** Filtros por candidato, veredito e ordem. "Ver dados e fonte" abre o motivo e o link.
- **Como ler** e **Como funciona.** O texto do site, inclusive o aviso de que a checagem é automática.

Vereditos: Verdadeiro (os dados confirmam), Impreciso (exagerado ou fora de contexto), Falso (os dados contradizem), Sem dados (não deu para verificar), Em revisão (o áudio não confirmou a frase; fica fora do placar).

## Rodar

Pré-requisito: Flutter estável (este projeto foi verificado com Flutter 3.47 / Dart 3.13).

```bash
flutter pub get
flutter analyze
flutter test
```

Android (emulador ou aparelho ligado):

```bash
flutter run
```

Gerar o APK:

```bash
flutter build apk
```

O arquivo sai em `build/app/outputs/flutter-apk/app-release.apk`.

iOS (somente num Mac, com Xcode):

```bash
cd ios && pod install && cd ..
flutter run
```

Pré-visualização no navegador:

```bash
flutter run -d web-server --web-port 43123 --web-hostname 0.0.0.0
```

Abra `http://127.0.0.1:43123`.

O app abre na **simulação**: um debate fictício que continua sozinho, com um aviso fixo de que os fatos são ilustrativos. Não precisa de rede.

Para ler um `placar.json` servido pelo pipeline nesta máquina:

```bash
flutter run --dart-define=PLACAR_SOURCE=live \
  --dart-define=PLACAR_BASE=http://127.0.0.1:8787/
```

O pipeline está em `pipeline/`. O site leve do debate (o produto de 23/10) está em `web/`. No GitHub Pages ele fica em `https://danilosilvadev.github.io/debate-mentirometro/` e abre na simulação. A casca que o Flutter usa no navegador foi para `flutter_web/`, para não disputar a pasta `web/` com o site estático.

## De onde vêm os dados

O site publica o placar em JSON, com polling a cada poucos segundos:

`https://placar-dados.zenithonacademy.com.br/placar.json`

Um debate passado usa o mesmo host: `placar-<arquivo>.json` (o site chama isso com `?d=`). Dois exemplos que existem hoje:

- `placar-2026-10-18.json`
- `placar-2026-10-18-ao-vivo.json` (o placar como ficou ao vivo, antes da revisão)

Não há um backend nosso. O app fala com esse JSON por cima de um repositório, e sempre pode rodar só com a simulação.

No app, o interruptor **Ao vivo** passa a buscar o JSON. Se a rede falhar, a tela avisa e dá para voltar à simulação.

Na linha de comando:

```bash
# abre já no placar publicado
flutter run --dart-define=PLACAR_SOURCE=live

# outro host (a URL precisa terminar em /)
flutter run --dart-define=PLACAR_SOURCE=live \
  --dart-define=PLACAR_BASE=https://exemplo.com/placar/

# um arquivo de debate passado: placar-2026-10-18.json
flutter run --dart-define=PLACAR_SOURCE=live \
  --dart-define=PLACAR_ARCHIVE=2026-10-18
```

`PLACAR_SOURCE` aceita `mock` (padrão) ou `live`.

### Encaixar outra fonte

A UI só enxerga `ScoreboardRepository` (`lib/src/domain/scoreboard_repository.dart`):

- `watch()` emite `ScoreboardSnapshot`
- `refresh()` busca de novo
- `dispose()` solta timer e conexão

Implementações que já vêm no projeto:

| Classe | Arquivo | O que faz |
| --- | --- | --- |
| `MockScoreboardRepository` | `lib/src/data/mock_scoreboard_repository.dart` | Roteiro local. A cada 3s revela um fato, ataque ou proposta. |
| `RemoteScoreboardRepository` | `lib/src/data/remote_scoreboard_repository.dart` | `GET` no JSON público a cada 6s, com `?t=` para furar o cache de 3s do site. |

O JSON é lido por `ScoreboardParser`. O formato é o do site: `candidatos` (`1` e `2`), `fatos[].declaracoes[]`, `propostas`, `ataques`, `linha` (minuto → `a1`/`p1`/`a2`/`p2`), `video`, `encerrado`, `revisao`.

Para uma fonte nova (WebSocket, arquivo, outro host):

1. Implemente `ScoreboardRepository`.
2. Devolva um `Scoreboard`. Se o payload for o JSON do site, use `ScoreboardParser.parse`.
3. Registre em `scoreboardRepositoryProvider`, em `lib/src/providers.dart`.

O contador de "pessoas assistindo" do site não está no JSON. Ele vem de um WebSocket em `wss://placar.zenithonacademy.com.br/ao-vivo`. A simulação mostra um número ilustrativo. O modo ao vivo não inventa audiência.

## Mentirômetro

A conta está em `lib/src/domain/mentiromentro.dart` e é a mesma do site:

- total checável = verdadeiro + impreciso + falso
- índice de erro = `(falso + impreciso / 2) / total`
- o ponteiro só se mexe com pelo menos 3 fatos checáveis de cada lado
- ângulo = `(erro da direita − erro da esquerda) × 90` graus (negativo pende para a esquerda)
- diferença menor que 0,1 no índice é empate técnico

Os testes em `test/mentiromentro_test.dart` cobrem meio ponto, exclusão de "Sem dados" e "Em revisão", o mínimo de 3, a escala do ponteiro e o empate.

## Licença

MIT. Copyright 2026 danilosilvadev. O texto está em `LICENSE`. Para enviar uma mudança, leia `CONTRIBUTING.md`.

Os JSON em `web/demo/` e as amostras do pipeline são fictícios. Não são a checagem de um debate real. O feed público `https://placar-dados.zenithonacademy.com.br/placar.json` pertence aos seus donos; este repositório só o lê quando alguém pede `?live=1`.
