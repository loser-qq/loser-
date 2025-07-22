print("Bot起動準備開始")  # 追加

import os
import re
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

print("ライブラリ読み込み完了")  # 追加

load_dotenv()
print("envロード完了")  # 追加

TOKEN = os.getenv("DISCORD_TOKEN")
print(f"TOKEN: {TOKEN}")  # 追加

ROLE_A_ID = int(os.getenv("ROLE_A_ID"))
ROLE_B_ID = int(os.getenv("ROLE_B_ID"))
ROLE_C_ID = int(os.getenv("ROLE_C_ID"))
SELF_INTRO_USER_IDS = [int(x) for x in os.getenv("SELF_INTRO_USER_IDS", "").split(",") if x]
SELF_INTRO_CHANNEL_IDS = [int(x) for x in os.getenv("SELF_INTRO_CHANNEL_IDS", "").split(",") if x]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1389799217865691186  # ←自分のサーバーIDに変更

# 1. /ロール付与
class RoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ロール付与", description="VC内のロールBをロールCに付け替え")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def switch_roles(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        role_a = guild.get_role(ROLE_A_ID)
        role_b = guild.get_role(ROLE_B_ID)
        role_c = guild.get_role(ROLE_C_ID)

        if role_a not in member.roles:
            await interaction.response.send_message("このコマンドを実行する権限がありません。", ephemeral=True)
            return

        if not member.voice or not member.voice.channel:
            await interaction.response.send_message("VCに参加してから実行してください。", ephemeral=True)
            return

        # まず仮応答
        await interaction.response.send_message("ロール付け替え処理中...", ephemeral=True)

        vc_members = member.voice.channel.members
        changed = 0
        for m in vc_members:
            if m.bot:
                continue
            if role_b in m.roles:
                await m.remove_roles(role_b)
                await m.add_roles(role_c)
                changed += 1

        # 結果を編集
        await interaction.edit_original_response(content=f"{changed}人のロールを付け替えました。")

# 2. メッセージリンク展開
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # メッセージリンクの正規表現
    link_pattern = r"https://discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)"
    matches = re.findall(link_pattern, message.content)
    for guild_id, channel_id, msg_id in matches:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            continue
        channel = guild.get_channel(int(channel_id))
        if not channel:
            continue
        try:
            target_msg = await channel.fetch_message(int(msg_id))
            content = target_msg.content
            if content:
                await message.channel.send(f"引用: {target_msg.author.display_name}「{content}」")
        except Exception as e:
            print(f"メッセージ展開失敗: {e}")

    await bot.process_commands(message)

# 3. 特定ユーザーがVC参加時に自己紹介DM
@bot.event
async def on_voice_state_update(member, before, after):
    # VC移動・退出時はスキップ
    if before.channel == after.channel or after.channel is None:
        return

    guild = member.guild
    vc_members = [m for m in after.channel.members if not m.bot]

    # VC内にSELF_INTRO_USER_IDSの誰かがいるか
    target_users = [m for m in vc_members if m.id in SELF_INTRO_USER_IDS]
    if not target_users:
        return

    # 参加してきた人（member）の自己紹介を探す
    intro_texts = []
    for intro_channel_id in SELF_INTRO_CHANNEL_IDS:
        intro_channel = guild.get_channel(intro_channel_id)
        if intro_channel is None:
            continue
        async for msg in intro_channel.history(limit=200):
            if msg.author.id == member.id:
                intro_texts.append(f"**{msg.author.display_name}** の自己紹介:\n{msg.content}")

    # VC内のSELF_INTRO_USER_IDSの人全員にDM送信
    if intro_texts:
        for target in target_users:
            try:
                await target.send("\n\n".join(intro_texts))
            except Exception as e:
                print(f"DM送信失敗: {e}")

async def setup_hook():
    await bot.add_cog(RoleCog(bot))
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"スラッシュコマンドを {len(synced)} 件同期しました (setup_hook)")
bot.setup_hook = setup_hook

@bot.event
async def on_ready():
    print(f"Bot起動: {bot.user}")

if __name__ == "__main__":
    bot.run(TOKEN)