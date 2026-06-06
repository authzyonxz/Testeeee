import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
import string

# ========================
# CONFIGURAÇÕES
# ========================
TOKEN = "SEU_TOKEN_AQUI"  # Substitua pelo token do seu bot
ADMIN_IDS = [123456789]   # Substitua pelo seu ID do Discord

PRECOS = {
    "1dia": 10,
    "7dias": 30,
    "30dias": 120
}

DATA_FILE = "dados.json"

# ========================
# FUNÇÕES DE DADOS
# ========================
def carregar_dados():
    if not os.path.exists(DATA_FILE):
        dados = {"estoques": {"1dia": [], "7dias": [], "30dias": []}, "saldos": {}}
        salvar_dados(dados)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DATA_FILE, "w") as f:
        json.dump(dados, f, indent=2)

# ========================
# BOT SETUP
# ========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ========================
# VIEWS / UI
# ========================

class QuantidadeModal(discord.ui.Modal, title="Quantidade de Keys"):
    def __init__(self, tipo: str):
        super().__init__()
        self.tipo = tipo
        self.quantidade = discord.ui.TextInput(
            label="Quantas keys você quer?",
            placeholder="Ex: 1",
            min_length=1,
            max_length=2
        )
        self.add_item(self.quantidade)

    async def on_submit(self, interaction: discord.Interaction):
        dados = carregar_dados()
        user_id = str(interaction.user.id)
        tipo = self.tipo

        try:
            qtd = int(self.quantidade.value)
            if qtd <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Quantidade inválida!", ephemeral=True)
            return

        estoque = dados["estoques"].get(tipo, [])
        saldo = dados["saldos"].get(user_id, 0)
        custo_total = PRECOS[tipo] * qtd
        nomes = {"1dia": "1 Dia", "7dias": "7 Dias", "30dias": "30 Dias"}

        if len(estoque) < qtd:
            await interaction.response.send_message(
                f"❌ Estoque insuficiente! Disponível: **{len(estoque)}** keys de {nomes[tipo]}.",
                ephemeral=True
            )
            return

        if saldo < custo_total:
            await interaction.response.send_message(
                f"❌ Saldo insuficiente!\n💰 Seu saldo: **{saldo} créditos**\n💸 Necessário: **{custo_total} créditos**",
                ephemeral=True
            )
            return

        view = ConfirmarCompraView(tipo, qtd, custo_total, nomes[tipo])
        embed = discord.Embed(
            title="🛒 Confirmar Compra",
            color=0xf0a500
        )
        embed.add_field(name="Plano", value=f"Key {nomes[tipo]}", inline=True)
        embed.add_field(name="Quantidade", value=str(qtd), inline=True)
        embed.add_field(name="Total", value=f"{custo_total} créditos", inline=True)
        embed.add_field(name="Seu saldo atual", value=f"{saldo} créditos", inline=True)
        embed.add_field(name="Saldo após compra", value=f"{saldo - custo_total} créditos", inline=True)
        embed.set_footer(text="Confirme sua compra abaixo")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmarCompraView(discord.ui.View):
    def __init__(self, tipo, qtd, custo_total, nome):
        super().__init__(timeout=60)
        self.tipo = tipo
        self.qtd = qtd
        self.custo_total = custo_total
        self.nome = nome

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        dados = carregar_dados()
        user_id = str(interaction.user.id)
        estoque = dados["estoques"].get(self.tipo, [])
        saldo = dados["saldos"].get(user_id, 0)

        if saldo < self.custo_total:
            await interaction.response.send_message("❌ Saldo insuficiente!", ephemeral=True)
            return
        if len(estoque) < self.qtd:
            await interaction.response.send_message("❌ Estoque insuficiente!", ephemeral=True)
            return

        keys_geradas = estoque[:self.qtd]
        dados["estoques"][self.tipo] = estoque[self.qtd:]
        dados["saldos"][user_id] = saldo - self.custo_total
        salvar_dados(dados)

        keys_texto = "\n".join([f"`{k}`" for k in keys_geradas])
        embed = discord.Embed(
            title=f"🔑 Suas Keys — {self.nome}",
            description=keys_texto,
            color=0x2ecc71
        )
        embed.set_footer(text="Obrigado pela compra! ✅")

        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Keys enviadas no seu privado!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ Compra confirmada! Mas não consigo te enviar DM.\nSuas keys:\n{keys_texto}",
                ephemeral=True
            )

        self.stop()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Compra cancelada.", ephemeral=True)
        self.stop()


class PanelSelect(discord.ui.Select):
    def __init__(self, dados):
        est1 = len(dados["estoques"].get("1dia", []))
        est7 = len(dados["estoques"].get("7dias", []))
        est30 = len(dados["estoques"].get("30dias", []))

        options = [
            discord.SelectOption(
                label=f"🔑 Key 1 Dia — 10 créditos",
                description=f"Estoque: {est1} disponíveis",
                value="1dia",
                emoji="1️⃣"
            ),
            discord.SelectOption(
                label=f"🔑 Key 7 Dias — 30 créditos",
                description=f"Estoque: {est7} disponíveis",
                value="7dias",
                emoji="7️⃣"
            ),
            discord.SelectOption(
                label=f"🔑 Key 30 Dias — 120 créditos",
                description=f"Estoque: {est30} disponíveis",
                value="30dias",
                emoji="3️⃣"
            ),
        ]
        super().__init__(placeholder="🛒 Selecione um plano...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        tipo = self.values[0]
        modal = QuantidadeModal(tipo=tipo)
        await interaction.response.send_modal(modal)


class PanelView(discord.ui.View):
    def __init__(self, dados):
        super().__init__(timeout=None)
        self.add_item(PanelSelect(dados))


# ========================
# COMANDOS SLASH
# ========================

@tree.command(name="panel", description="Abre o painel de geração de keys")
async def panel(interaction: discord.Interaction):
    dados = carregar_dados()
    est1  = len(dados["estoques"].get("1dia", []))
    est7  = len(dados["estoques"].get("7dias", []))
    est30 = len(dados["estoques"].get("30dias", []))

    embed = discord.Embed(
        title="🔑 Key Generator — Loja",
        description="Selecione o plano desejado abaixo para gerar suas keys!",
        color=0x5865F2
    )
    embed.add_field(
        name="1️⃣  Key 1 Dia",
        value=f"💰 **10 créditos**\n📦 Estoque: **{est1}** disponíveis",
        inline=False
    )
    embed.add_field(
        name="7️⃣  Key 7 Dias",
        value=f"💰 **30 créditos**\n📦 Estoque: **{est7}** disponíveis",
        inline=False
    )
    embed.add_field(
        name="🗓️  Key 30 Dias",
        value=f"💰 **120 créditos**\n📦 Estoque: **{est30}** disponíveis",
        inline=False
    )
    embed.set_footer(text="Use o menu abaixo para comprar suas keys")

    await interaction.response.send_message(embed=embed, view=PanelView(dados))


@tree.command(name="addestoque", description="[ADMIN] Adiciona keys ao estoque")
@app_commands.describe(
    tipo="Tipo da key (1dia, 7dias, 30dias)",
    keys="Keys separadas por linha (cole tudo em uma mensagem)"
)
@app_commands.choices(tipo=[
    app_commands.Choice(name="1 Dia", value="1dia"),
    app_commands.Choice(name="7 Dias", value="7dias"),
    app_commands.Choice(name="30 Dias", value="30dias"),
])
async def addestoque(interaction: discord.Interaction, tipo: str, keys: str):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    dados = carregar_dados()
    lista = [k.strip() for k in keys.strip().splitlines() if k.strip()]
    dados["estoques"][tipo].extend(lista)
    salvar_dados(dados)

    nomes = {"1dia": "1 Dia", "7dias": "7 Dias", "30dias": "30 Dias"}
    await interaction.response.send_message(
        f"✅ **{len(lista)}** keys adicionadas ao estoque de **{nomes[tipo]}**!\n"
        f"📦 Total agora: **{len(dados['estoques'][tipo])}** keys",
        ephemeral=True
    )


@tree.command(name="limparestoque", description="[ADMIN] Limpa todo o estoque de keys")
async def limparestoque(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    dados = carregar_dados()
    dados["estoques"] = {"1dia": [], "7dias": [], "30dias": []}
    salvar_dados(dados)
    await interaction.response.send_message("🗑️ Estoque limpo com sucesso!", ephemeral=True)


@tree.command(name="addsaldo", description="[ADMIN] Adiciona saldo a um usuário")
@app_commands.describe(usuario="Usuário do Discord", valor="Quantidade de créditos a adicionar")
async def addsaldo(interaction: discord.Interaction, usuario: discord.Member, valor: int):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    if valor <= 0:
        await interaction.response.send_message("❌ O valor deve ser positivo!", ephemeral=True)
        return

    dados = carregar_dados()
    user_id = str(usuario.id)
    dados["saldos"][user_id] = dados["saldos"].get(user_id, 0) + valor
    salvar_dados(dados)

    await interaction.response.send_message(
        f"✅ **{valor} créditos** adicionados para {usuario.mention}!\n"
        f"💰 Saldo atual: **{dados['saldos'][user_id]} créditos**",
        ephemeral=True
    )


@tree.command(name="saldo", description="Veja seu saldo de créditos")
async def saldo(interaction: discord.Interaction):
    dados = carregar_dados()
    user_id = str(interaction.user.id)
    s = dados["saldos"].get(user_id, 0)
    await interaction.response.send_message(
        f"💰 Seu saldo: **{s} créditos**",
        ephemeral=True
    )


@tree.command(name="estoque", description="[ADMIN] Veja o estoque atual")
async def estoque(interaction: discord.Interaction):
    if interaction.user.id not in ADMIN_IDS:
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
        return

    dados = carregar_dados()
    embed = discord.Embed(title="📦 Estoque Atual", color=0x3498db)
    embed.add_field(name="1 Dia",   value=f"{len(dados['estoques']['1dia'])} keys",   inline=True)
    embed.add_field(name="7 Dias",  value=f"{len(dados['estoques']['7dias'])} keys",  inline=True)
    embed.add_field(name="30 Dias", value=f"{len(dados['estoques']['30dias'])} keys", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ========================
# EVENTOS
# ========================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Bot online como {bot.user}")
    print(f"📡 Comandos sincronizados!")

bot.run(TOKEN)
