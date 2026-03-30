# Como Configurar o Dashboard Ademicon Vila Olimpia

Este guia explica passo a passo como publicar o dashboard na internet usando o GitHub Pages, sem necessidade de conhecimento tecnico.

---

## O que voce vai precisar

- Uma conta no GitHub (gratuita) - site: **github.com**
- Sua chave de API do Apollo CRM
- Os arquivos do dashboard (esta pasta)

---

## Passo 1: Criar sua conta no GitHub

1. Acesse **github.com** no seu navegador
2. Clique no botao verde **Sign up** (Cadastrar)
3. Preencha:
   - Username (nome de usuario): escolha algo simples, ex: `ademicon-vo`
   - Email: seu email profissional
   - Password: uma senha forte
4. Siga as instrucoes de verificacao de email
5. Quando terminar, voce vai ver a pagina inicial do GitHub com o seu nome no canto superior direito

---

## Passo 2: Criar o repositorio e fazer upload dos arquivos

### 2.1 - Criar um novo repositorio

1. Na pagina inicial do GitHub, clique no botao verde **New** (ou no icone de `+` no canto superior direito e escolha **New repository**)
2. Preencha os campos:
   - **Repository name**: `ademicon-dashboard` (exatamente assim, sem espacos)
   - **Description**: Dashboard Operacional Ademicon Vila Olimpia
   - Marque a opcao **Public** (publico - necessario para o GitHub Pages gratuito)
   - Deixe as outras opcoes como estao
3. Clique em **Create repository** (Criar repositorio)

### 2.2 - Fazer upload dos arquivos

Voce vai ver uma pagina vazia com instrucoes. Faca o seguinte:

1. Clique no link **uploading an existing file** (enviar um arquivo existente)
2. Arraste todos os arquivos desta pasta para a area indicada na tela, OU clique em **choose your files** para selecionar manualmente:
   - `index.html`
   - `team.html`
   - `data.json`
3. Role a pagina para baixo e clique em **Commit changes** (salvar alteracoes)

### 2.3 - Upload das pastas (scripts e .github)

Como o GitHub nao permite arrastar pastas diretamente pela interface web, siga estes passos para cada pasta:

**Para a pasta `scripts/`:**
1. Na pagina do repositorio, clique em **Add file** e depois **Create new file**
2. No campo de nome, digite: `scripts/fetch_apollo.py`
3. Abra o arquivo `fetch_apollo.py` desta pasta no Bloco de Notas, selecione tudo (Ctrl+A) e copie (Ctrl+C)
4. Cole o conteudo na area de texto do GitHub
5. Clique em **Commit new file**

**Para a pasta `.github/workflows/`:**
1. Clique em **Add file** e depois **Create new file**
2. No campo de nome, digite: `.github/workflows/sync-apollo.yml`
3. Abra o arquivo `sync-apollo.yml` desta pasta no Bloco de Notas, selecione tudo e copie
4. Cole o conteudo na area de texto do GitHub
5. Clique em **Commit new file**

---

## Passo 3: Ativar o GitHub Pages

1. Dentro do repositorio, clique na aba **Settings** (Configuracoes) - barra superior
2. No menu lateral esquerdo, clique em **Pages**
3. Em **Source** (Fonte), clique no menu suspenso e selecione **Deploy from a branch**
4. Em **Branch**, selecione **main** e a pasta **/ (root)**
5. Clique em **Save** (Salvar)
6. Aguarde alguns minutos (geralmente 2 a 5 minutos)
7. A pagina sera atualizada e mostrara um banner verde com o link do seu site:
   `https://SEU-USUARIO.github.io/ademicon-dashboard/`

---

## Passo 4: Configurar a chave do Apollo CRM

Para que o dashboard busque dados automaticamente do Apollo CRM, voce precisa adicionar sua chave de API como um "segredo" (secret) no GitHub.

### Como encontrar sua chave de API no Apollo

1. Acesse o Apollo CRM e faca login
2. Clique no seu perfil (canto superior direito)
3. Va em **Settings** (Configuracoes)
4. Clique em **Integrations** e depois em **API**
5. Copie o valor da **API Key**

### Como adicionar o segredo no GitHub

1. No repositorio do GitHub, clique em **Settings**
2. No menu lateral, clique em **Secrets and variables** e depois em **Actions**
3. Clique no botao **New repository secret**
4. Preencha:
   - **Name**: `APOLLO_API_KEY` (exatamente assim, em maiusculas)
   - **Secret**: cole aqui a sua chave de API do Apollo
5. Clique em **Add secret**

Pronto! A partir de agora, o sistema vai buscar dados do Apollo automaticamente a cada 30 minutos.

---

## Passo 5: Acessar o dashboard

Apos o GitHub Pages estar ativo, voce pode acessar:

- **View Gestao (privada):**
  `https://SEU-USUARIO.github.io/ademicon-dashboard/`

- **View Time (TV do escritorio):**
  `https://SEU-USUARIO.github.io/ademicon-dashboard/team.html`

Substitua `SEU-USUARIO` pelo nome de usuario que voce escolheu no Passo 1.

**Exemplo:** se seu usuario e `ademicon-vo`, os links serao:
- `https://ademicon-vo.github.io/ademicon-dashboard/`
- `https://ademicon-vo.github.io/ademicon-dashboard/team.html`

---

## Como atualizar dados manualmente (sem esperar 30 minutos)

1. No GitHub, va ao repositorio do dashboard
2. Clique na aba **Actions** (Acoes)
3. No menu lateral, clique em **Sync Apollo CRM Data**
4. Clique no botao **Run workflow** (Executar fluxo de trabalho)
5. Clique novamente em **Run workflow** para confirmar
6. Aguarde cerca de 1 minuto. Quando aparecer um circulo verde, os dados foram atualizados.
7. Recarregue o dashboard no navegador para ver os novos dados.

---

## Como marcar acoes do plano como concluidas

As acoes do Plano de 90 Dias podem ser marcadas diretamente no dashboard (clique na caixa de selecao ao lado de cada acao). O status e salvo automaticamente no navegador.

Se quiser que o status seja permanente e visivel para todos:

1. No GitHub, abra o arquivo `data.json` clicando nele
2. Clique no icone de lapis (editar) no canto superior direito do arquivo
3. Encontre a acao que deseja atualizar. Exemplo:
   ```json
   {"id": "1.1", "texto": "Configurar escritorio...", "responsavel": "Raphael + Wagner", "status": "pendente"}
   ```
4. Altere o valor de `"status"` para um dos seguintes:
   - `"pendente"` - ainda nao iniciada (circulo cinza)
   - `"em_andamento"` - em progresso (circulo laranja pulsante)
   - `"concluido"` - finalizada (circulo verde)
5. Clique em **Commit changes** para salvar
6. Aguarde 2-3 minutos para o GitHub Pages atualizar

---

## Perguntas frequentes

**O dashboard nao esta carregando os dados. O que fazer?**
Verifique se o arquivo `data.json` existe no repositorio e se o GitHub Pages esta ativo em Settings > Pages.

**Os dados nao estao sendo atualizados automaticamente.**
Verifique se o segredo `APOLLO_API_KEY` foi configurado corretamente em Settings > Secrets and variables > Actions.

**Quero mostrar a TV do time em tela cheia.**
Abra `team.html` no navegador e pressione F11 para entrar em modo tela cheia.

**Como adicionar um novo consultor antes de ter dados do Apollo?**
Edite o arquivo `data.json` no GitHub e adicione um objeto na lista `"consultores"`:
```json
{
  "nome": "Nome do Consultor",
  "vgv_semana": 0,
  "vgv_mes": 0,
  "contratos_mes": 0,
  "leads_ativos": 0,
  "prospecoes": 0
}
```

---

## Suporte

Em caso de duvidas, entre em contato com a equipe de tecnologia ou consulte a documentacao do GitHub Pages em: **docs.github.com/pages**
