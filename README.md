
## 🎥 Inspiração

<img src="img/youtube.jpeg" alt="Thumb do vídeo do Lucas Montano" width="100%" />

**Resumo curto sobre o tema principal do vídeo:**

Lucas Montano comenta sobre um aplicativo criado por um desenvolvedor chamado Roy que permite "trapacear" em entrevistas técnicas ao resolver problemas de *LeetCode* com ajuda de IA sem que o entrevistador perceba. O app gerou mais de R$1 milhão em receita. Lucas recria a ideia em apenas uma hora para mostrar como, com inteligência artificial, o tempo e esforço para lançar MVPs caiu drasticamente. Ele também resolve um problema nível *hard* do *LeetCode* e provoca reflexões sobre o futuro das entrevistas técnicas e o papel da IA nesse processo.

---
https://www.youtube.com/watch?v=O_kcf7R7ZqE&t=497s


Canvas # 🌌 Projeto Falcon – Agentes Inteligentes em Python

Um conjunto de agentes independentes que se comunicam via RabbitMQ e utilizam OpenAI para executar tarefas como capturar tela, gravar áudio, descrever imagens, transcrever fala e processar prompts de texto.

---
## 🧰 Pré-requisitos

- Python **3.8+**
- Node.js **16+** (para a interface Electron `x-wing`)
- Docker e Docker Compose (para subir o RabbitMQ)
- OpenAI API Key válida
- Ambiente gráfico (necessário para captura de tela)
- Microfone ativo (para gravação de áudio)

---

## ⚙️ Configuração do Ambiente

### 1. Clone o projeto e acesse a pasta

```bash
git clone https://github.com/seu-usuario/falcon-agents.git
cd falcon-agents
```

### 2. Crie o arquivo `.env` com suas credenciais

```env
OPENAI_API_KEY=your_openai_api_key
RABBITMQ_URI=amqp://falcon:falcon@localhost:5672/
```

### 3. Instale as dependências Python

```bash
pip install -r requirements.txt
```

### 4. Inicie o RabbitMQ com Docker

```bash
docker-compose up -d
```

Acesse o painel em: [http://localhost:15672](http://localhost:15672)  
Usuário: `falcon` • Senha: `falcon`

---

## 🚀 Como iniciar todos os agentes

Execute o orquestrador:

```bash
python3 start.py
```

---

## 🤖 Agentes Disponíveis

<img src="img/img.png" alt="Thumb do vídeo do Lucas Montano" width="100%" />

___

>### 001-Han Solo Agent

<img src="img/han_solo.png"/>

Escuta o teclado, Envia eventos para fila rabbitMQ:

- `Ctrl + Alt + M` → Screenshot
- `Ctrl + Alt + S` → Iniciar gravação de áudio
- `Ctrl + Alt + R` → Parar gravação de áudio

```bash

python3 han_solo.py

```
___

>### 002-Luke Agent

<img src="img/han_solo.png"/>

Captura screenshots envia para fila `QUEUE_FALCON_DESCRIBE` (C3Po).

```bash

python3 luke.py

```
___

>### 003-C-3PO Agent

<img src="img/c3po.png"/>

Recebe o caminho de uma imagem pela fila `QUEUE_FALCON_DESCRIBE` descreve a imagem e envia a descrição da imagem para `QUEUE_FALCON_ASK`.


```bash

python3 c3po.py

```
___

>### 004-Yoda Agent

<img src="img/yoda.png"/>

Recebe prompts de texto pela fila `QUEUE_FALCON_ASK` e responde com o modelo **GPT-4o**.

- Resultado enviado para `QUEUE_FALCON_X_WING`

```bash

python3 yoda.py

```

___

>### 005-Leia

<img src="img/leia.png"/>

Grava áudio a partir de comandos recebidos em `QUEUE_FALCON_AUDIO`.

```bash

python3 leia.py

```
___

>### 006-Obi Wab

<img src="img/obiwan.png"/>

Transcreve arquivos de áudio (.mp3) usando o modelo **Whisper** da OpenAI.

- Escuta `QUEUE_FALCON_TO_SPEECH`
- Resposta vai para `QUEUE_FALCON_X_WING`

```bash

python3 obi_wan.py

```
### 🚗 X-Wing Agent (Interface em Electron)

**X-Wing** é a interface visual da frota Falcon. Um app leve em Electron que permite ao usuário:
- Enviar prompts diretamente para o GPT-4o
- Iniciar e parar gravações de áudio
- Capturar a tela
- Visualizar respostas recebidas via RabbitMQ

#### 📂 Localização
Pasta: `x-wing/`

#### 🔧 Instalação

```bash
cd x-wing
npm install
```

#### ▶️ Execução

```bash
npm run build && npm start
```

Modo desenvolvimento:

```bash
npm run dev
```

---

## 🌐 Docker – Serviço RabbitMQ

```yaml
services:
  falcon-rabbitmq:
    image: rabbitmq:management
    container_name: falcon-rabbitmq
    restart: unless-stopped
    environment:
      RABBITMQ_DEFAULT_USER: falcon
      RABBITMQ_DEFAULT_PASS: falcon
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - app-network

networks:
  app-network:
    driver: bridge
    name: app-network
```

---

## 📁 Estrutura do Projeto

```
falcon-agents/
├── start.py
├── luke.py
├── leia.py
├── yoda.py
├── han_solo.py
├── obi_wan.py
├── c3po.py
├── consts.py
├── .env
├── docker-compose.yml
├── requirements.txt
└── x-wing/  # Interface Electron
```

---

### 🧠 Considerações

Este material foi desenvolvido exclusivamente para fins educacionais. O uso inadequado de ferramentas de inteligência artificial pode gerar consequências negativas, especialmente para profissionais da área de tecnologia. Utilize com responsabilidade e consciência.


> ⚠️ **Atenção**: para que a janela do assistente permaneça oculta durante o uso, é necessário compartilhar apenas a janela específica do navegador ou aplicativo. O modo de compartilhamento de tela completa pode revelar a interface do assistente ao entrevistador.

Se este projeto foi útil ou te inspirou de alguma forma, considere apoiar o desenvolvedor com uma doação via PIX. Seu apoio é essencial para manter o projeto ativo, evoluindo e acessível para mais pessoas.

Todo este conteúdo foi criado com o auxílio de inteligência artificial, demonstrando como essa tecnologia pode acelerar o desenvolvimento de ideias e MVPs.



<img src="img/pix.png" alt="Chave PIX" width="300" />

Chave PIX: **marcelo.tobbias@gmail.com**

ou

### https://buy.stripe.com/test_14k9DZ7jxcZucPS9AA

## 👥 Contato e Repositório

- GitHub: [https://github.com/mtobbias/mister-m](https://github.com/mtobbias/mister-m)
- LinkedIn: [https://www.linkedin.com/in/brdevmtobias/](https://www.linkedin.com/in/brdevmtobias/)
- E-mail: marcelo.tobbias@gmail.com
- Youtube: https://www.youtube.com/@dev-mister-m
