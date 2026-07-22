import discord
from discord.ext import commands
import asyncio
import os

# Thiết lập các quyền truy cập (Intents) cho Bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Khởi tạo Bot với tiền tố lệnh là dấu chấm hỏi (?)
bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)

# Khởi tạo ID Owner (Cố định quyền tối cao) và danh sách Admin
owner_id = 1392559367529828414
admin_ids = set()

# Các biến kiểm soát luồng bất đồng bộ (Task & Voice Connection)
spam_task = None
tag_task = None
voice_client = None

# Biến cờ hiệu kiểm soát trạng thái dừng nhanh lập tức
is_spamming = False
is_tagging = False

# Biến lưu trữ cấu hình âm lượng toàn cục
current_volume = "1.0" 
current_filename = None

# Hàm kiểm tra quyền thực thi lệnh (Owner hoặc Admin)
def is_authorized(ctx):
    return ctx.author.id == owner_id or ctx.author.id in admin_ids

# Hàm kiểm tra quyền tối cao (Chỉ dành cho duy nhất Owner)
def is_owner(ctx):
    return ctx.author.id == owner_id

@bot.event
async def on_ready():
    print(f"Hệ thống đã sẵn sàng. Tài khoản Bot: {bot.user}")

# --- MENU TRỢ GIÚP LỆNH ---
@bot.command(name="menu")
async def show_menu(ctx):
    embed = discord.Embed(
        title="🤖 HỆ THỐNG ĐIỀU KHIỂN & LỆNH ĐIỀU HÀNH",
        description="Chào mừng bạn đến với các lệnh vui vẻ. Toàn bộ danh sách lệnh đã được phân loại chi tiết theo chức năng bên dưới.",
        color=discord.Color.from_rgb(46, 204, 113)
    )
    
    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)
        
    embed.add_field(
        name="👑 ĐẶC QUYỀN OWNER (CHỦ SỞ HỮU)",
        value=(
            "`?addfile [tên_file] [nội dung]` ➔ Tạo file mới\n"
            "`?delfile [tên_file]` ➔ Xóa file\n"
            "`?addmusic [tên_nhạc.mp3]` ➔ Thêm tệp âm thanh\n"
            "`?delmusic [tên_file]` ➔ Xóa file nhạc\n"
            "`?status [nội dung]` ➔ Thay đổi trạng thái bot\n"
            "`?addadmin [ID]` ➔ Thêm Quyền Admin\n"
            "`?deladmin [ID]` ➔ Xóa quyền Admin"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💬 (SPAM / TAG)",
        value=(
            "`?nhaytag [ID_Kênh] [Mục_Tiêu] [tên_file]` ➔ nhaytag \n"
            "`?stoptag` ➔ Dừng nhaytag\n"
            "`?spam [ID_Kênh] [Nội dung]` ➔ Bắt đầu spam vui vẻ\n"
            "`?stopspam` ➔ Dừng spam\n"
            "`?listfile` ➔ Các tệp trong file bot hiện có"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔊 ĐIỀU KHIỂN VOICE & KHUẾCH ĐẠI ÂM THANH",
        value=(
            "`?join [ID_Kênh_Voice] [tên_file.mp3]` ➔ Xa\n"
            "`?stopvoice` ➔ Dừng xa\n"
            "`?listmusic` ➔ danh sách nhac \n"
            "`?volume [số]` ➔ Đặt hệ số nhân âm lượng\n"
            "`?boost [số]` ➔ Đẩy siêu tăng cường công suất âm thanh cực đại\n"
            "`?db [số]` ➔ Cấu hình tăng volume theo đơn vị Decibel"
        ),
        inline=False
    )

    embed.add_field(
        name="⚙️ KIỂM TRA HỆ THỐNG & TIỆN ÍCH",
        value=(
            "`?listadmin` ➔ Hiển thị danh sách admin\n"
            "`?av [@user hoặc ID]` ➔ Xem ảnh đại diện "
        ),
        inline=False
    )
    
    user_avatar_url = ctx.author.avatar.url if ctx.author.avatar else None
    embed.set_footer(
        text=f"Yêu cầu bởi: {ctx.author.name} •  '?'",
        icon_url=user_avatar_url
    )
    
    await ctx.send(embed=embed)

# --- LỆNH XEM AVATAR (MỌI NGƯỜI DÙNG ĐỀU DÙNG ĐƯỢC) ---
@bot.command(name="av")
async def get_avatar(ctx, *, member: discord.User = None):
    # Nếu không tag hoặc không nhập ID ai đó, mặc định lấy avatar của chính người gọi lệnh
    if member is None:
        member = ctx.author

    embed = discord.Embed(
        title=f"🖼️ AVATAR CỦA {member.name}",
        color=discord.Color.from_rgb(52, 152, 219)
    )
    
    avatar_url = member.display_avatar.url
    embed.set_image(url=avatar_url)
    
    embed.add_field(
        name="🔗 Đường dẫn trực tiếp",
        value=f"[Bấm vào đây để tải ảnh gốc]({avatar_url})",
        inline=False
    )
    
    user_avatar_url = ctx.author.avatar.url if ctx.author.avatar else None
    embed.set_footer(
        text=f"Yêu cầu bởi: {ctx.author.name}",
        icon_url=user_avatar_url
    )
    
    await ctx.send(embed=embed)

@bot.command(name="addfile")
async def add_file(ctx, filename: str, *, content: str = None):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx): 
        await ctx.send("❌ Lệnh này yêu cầu đặc quyền tối cao của Owner.")
        return

    if not filename.endswith('.txt'):
        filename += '.txt'

    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith('.txt'):
            try:
                await attachment.save(filename)
                await ctx.send(f"✅ [Owner] Đã tải và lưu file `{filename}` thành công từ tệp đính kèm!")
                return
            except Exception as e:
                await ctx.send(f"❌ Lỗi khi lưu tệp đính kèm: {e}")
                return
        else:
            await ctx.send("❌ Tệp đính kèm phải có định dạng văn bản `.txt`.")
            return

    if not content:
        await ctx.send("❌ Vui lòng nhập nội dung văn bản hoặc đính kèm một file `.txt`.")
        return

    try:
        formatted_content = content.replace("\\n", "\n")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        await ctx.send(f"✅ [Owner] Đã tạo/ghi đè file `{filename}` thành công!")
    except Exception as e:
        await ctx.send(f"❌ Không thể ghi file: {e}")

# --- XÓA FILE NHAYTAG (.TXT) ---
@bot.command(name="delfile")
async def del_file(ctx, filename: str):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx):
        await ctx.send("❌ Lệnh này yêu cầu đặc quyền tối cao của Owner.")
        return

    if not filename.endswith('.txt'):
        filename += '.txt'

    if not os.path.exists(filename):
        await ctx.send(f"❌ Không tìm thấy file text `{filename}` trong thư mục.")
        return

    try:
        os.remove(filename)
        clean_name = os.path.splitext(filename)[0]
        await ctx.send(f"🗑️ [Owner] Đã xóa thành công file nhaytag: `{clean_name}`")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi xóa file: {e}")

@bot.command(name="addmusic")
async def add_music(ctx, filename: str = None):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx):
        await ctx.send("❌ Lệnh này yêu cầu đặc quyền tối cao của Owner.")
        return

    if not ctx.message.attachments:
        await ctx.send("❌ Bạn chưa đính kèm tệp âm thanh nào cả! Vui lòng upload file cùng lúc khi gõ lệnh.")
        return

    attachment = ctx.message.attachments[0]
    valid_extensions = ('.mp3', '.wav', '.m4a', '.ogg')
    
    if not attachment.filename.lower().endswith(valid_extensions):
        await ctx.send("❌ Định dạng tệp đính kèm không hợp lệ. Bot chỉ nhận đuôi: `.mp3`, `.wav`, `.m4a`, `.ogg`.")
        return

    if not filename:
        filename = attachment.filename
    else:
        if not filename.lower().endswith(valid_extensions):
            orig_ext = os.path.splitext(attachment.filename)[1]
            filename += orig_ext

    try:
        await attachment.save(filename)
        await ctx.send(f"✅ [Owner] Đã nạp thành công file âm thanh: `{filename}`")
    except Exception as e:
        await ctx.send(f"❌ Thất bại khi lưu file nhạc vào bộ nhớ: {e}")

# --- XÓA FILE NHẠC (AUDIO) ---
@bot.command(name="delmusic")
async def del_music(ctx, filename: str):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx):
        await ctx.send("❌ Lệnh này yêu cầu đặc quyền tối cao của Owner.")
        return

    valid_extensions = ('.mp3', '.wav', '.m4a', '.ogg')
    
    target_file = filename
    if not filename.lower().endswith(valid_extensions):
        found = False
        for ext in valid_extensions:
            if os.path.exists(filename + ext):
                target_file = filename + ext
                found = True
                break
        if not found:
            target_file = filename + '.mp3'
    
    if not os.path.exists(target_file):
        await ctx.send(f"❌ Không tìm thấy tệp âm thanh `{filename}` trong thư mục.")
        return

    global current_filename, voice_client
    if voice_client and voice_client.is_playing() and current_filename == target_file:
        await ctx.send(f"⚠️ Tệp `{target_file}` đang được phát trong kênh Voice! Vui lòng dùng lệnh `?stopvoice` trước khi xóa.")
        return

    try:
        os.remove(target_file)
        await ctx.send(f"🗑️ [Owner] Đã xóa thành công file nhạc: `{target_file}`")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi xóa file nhạc: {e}")

@bot.command(name="listfile")
async def list_file(ctx):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    files = [f for f in os.listdir('.') if f.lower().endswith('.txt') and os.path.isfile(f)]
    
    if not files:
        await ctx.send("📁 Không có file cấu hình `.txt` nào trong thư mục.")
        return
        
    file_list = "\n".join([f"- `{os.path.splitext(f)[0]}`" for f in files])
    await ctx.send(f"**📁 Danh sách file text nhaytag sẵn có:**\n{file_list}")

# --- TÍNH NĂNG SPAM ---
async def loop_sender(target_channel, content):
    global is_spamming
    while is_spamming:
        try:
            await target_channel.send(content)
        except Exception:
            pass
        await asyncio.sleep(0.65)

@bot.command(name="spam")
async def start_spam(ctx, target_channel_id: int, *, content: str):
    global spam_task, is_spamming
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    is_spamming = False
    if spam_task and not spam_task.done():
        spam_task.cancel()
        
    target_channel = bot.get_channel(target_channel_id) or await bot.fetch_channel(target_channel_id)
    if not target_channel:
        await ctx.send("❌ Không tìm thấy kênh với ID đã cung cấp.")
        return
        
    is_spamming = True
    spam_task = asyncio.create_task(loop_sender(target_channel, content))
    await ctx.send(f"▶️ Bắt đầu spam vào kênh <#{target_channel_id}> ")

@bot.command(name="stopspam")
async def stop_spam(ctx):
    global spam_task, is_spamming
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    is_spamming = False 
    if spam_task:
        spam_task.cancel()
        spam_task = None
    await ctx.send("⏹️ Đã dừng spam .")

# --- TÍNH NĂNG NHAYTAG ---
async def loop_tag_file_sender(target_channel, mention_target, filepath):
    global is_tagging
    smiley_patterns = ["=))", "==))", ":)", ":D", "^^", "=]", "=)", ";)", ":]", ":]]", "đê", "nha", "á"]
    
    if not os.path.exists(filepath):
        await target_channel.send(f"❌ File nội dung không tồn tại.")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        await target_channel.send("⚠️ File nội dung rỗng. Hủy tiến trình tag.")
        return
        
    mention_clean = mention_target.strip()
    line_count = len(lines)
    index = 0
    
    while is_tagging:
        line = lines[index]
        index = (index + 1) % line_count

        matched_smiley = None
        for smiley in smiley_patterns:
            if line.endswith(smiley):
                matched_smiley = smiley
                break
        
        if matched_smiley:
            base_text = line[:-len(matched_smiley)].rstrip()
            full_content = f"{base_text} {mention_clean} {matched_smiley}"
        else:
            full_content = f"{line} {mention_clean}"
        
        try:
            await target_channel.send(full_content)
        except Exception:
            pass
            
        await asyncio.sleep(0.65)

@bot.command(name="nhaytag")
async def start_tag(ctx, target_channel_id: int, mention_target: str, filename: str):
    global tag_task, is_tagging
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    if not filename.endswith('.txt'):
        filename += '.txt'
        
    is_tagging = False
    if tag_task and not tag_task.done():
        tag_task.cancel()
        
    if not os.path.exists(filename):
        clean_name = os.path.splitext(filename)[0]
        await ctx.send(f"❌ Tệp tin nội dung `{clean_name}` không tồn tại. Hãy dùng lệnh `?addfile` trước.")
        return
        
    target_channel = bot.get_channel(target_channel_id) or await bot.fetch_channel(target_channel_id)
    if not target_channel:
        await ctx.send("❌ Không tìm thấy kênh với ID đã cung cấp.")
        return
        
    is_tagging = True
    tag_task = asyncio.create_task(loop_tag_file_sender(target_channel, mention_target, filename))
    print_name = os.path.splitext(filename)[0]
    await ctx.send(f"▶️ Bắt đầu nhaytag `{print_name}`  `{mention_target}` vào kênh <#{target_channel_id}>.")

@bot.command(name="stoptag")
async def stop_tag(ctx):
    global tag_task, is_tagging
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    is_tagging = False 
    if tag_task:
        tag_task.cancel()
        tag_task = None
    await ctx.send("⏹️ Đã dừng nhaytag .")

async def reload_audio(ctx):
    global voice_client, current_filename, current_volume
    if not voice_client or not voice_client.is_connected() or not current_filename:
        return

    if voice_client.is_playing():
        voice_client.stop()

    ffmpeg_options = {
        'options': f'-vn -filter:a "volume={current_volume}"'
    }
    
    executable_path = "ffmpeg"
    if os.path.exists("ffmpeg.exe"):
        executable_path = "ffmpeg.exe"
    elif os.path.exists("./ffmpeg"):
        executable_path = "./ffmpeg"

    try:
        source = discord.FFmpegPCMAudio(current_filename, executable=executable_path, **ffmpeg_options)
        voice_client.play(source)
    except Exception as e:
        await ctx.send(f"❌ Lỗi áp dụng cấu hình âm thanh mới: {e}")

@bot.command(name="join")
async def join_and_play(ctx, voice_channel_id: int, filename: str):
    global voice_client, current_filename, current_volume
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    if not os.path.exists(filename):
        await ctx.send(f"❌ Tệp tin âm thanh `{filename}` không tồn tại.")
        return

    channel = bot.get_channel(voice_channel_id)
    if not channel:
        try:
            channel = await bot.fetch_channel(voice_channel_id)
        except Exception:
            await ctx.send("❌ Không tìm thấy kênh thoại với ID đã cung cấp.")
            return

    if not isinstance(channel, discord.VoiceChannel):
        await ctx.send("❌ ID đã cung cấp không phải là một kênh thoại.")
        return

    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != voice_channel_id:
                await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
    except Exception as e:
        await ctx.send(f"❌ Lỗi kết nối kênh thoại: {e}")
        return
        
    current_filename = filename

    if voice_client.is_playing():
        voice_client.stop()

    ffmpeg_options = {
        'options': f'-vn -filter:a "volume={current_volume}"'
    }
    
    executable_path = "ffmpeg"
    if os.path.exists("ffmpeg.exe"):
        executable_path = "ffmpeg.exe"
    elif os.path.exists("./ffmpeg"):
        executable_path = "./ffmpeg"

    try:
        source = discord.FFmpegPCMAudio(filename, executable=executable_path, **ffmpeg_options)
        voice_client.play(source)
        await ctx.send(f"🎵 Đã vào kênh <#{voice_channel_id}> và phát: `{filename}`")
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi phát nhạc: {e}")

@bot.command(name="stopvoice")
async def stop_voice(ctx):
    global voice_client, current_filename
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    if voice_client and voice_client.is_connected():
        if voice_client.is_playing():
            voice_client.stop()
        await voice_client.disconnect()
        voice_client = None
        current_filename = None
        await ctx.send("⏹️ Đã dừng phát âm thanh và ngắt kết nối.")
    else:
        await ctx.send("❌ Hiện tại Bot không ở trong kênh Voice.")

@bot.command(name="volume")
async def change_volume(ctx, gain: str):
    global current_volume
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return

    current_volume = gain
    await ctx.send(f"🔊 Đã cấu hình hệ số âm lượng mục tiêu thành: `{gain}` lần.")
    if voice_client and voice_client.is_connected() and voice_client.is_playing():
        await reload_audio(ctx)

@bot.command(name="boost")
async def boost_volume(ctx, boost_factor: str):
    global current_volume
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return

    current_volume = boost_factor
    await ctx.send(f"🚀 Kích hoạt siêu Boost! Hệ số khuếch đại: `{boost_factor}` lần.")
    if voice_client and voice_client.is_connected() and voice_client.is_playing():
        await reload_audio(ctx)

@bot.command(name="db")
async def change_db(ctx, db_value: str):
    global current_volume
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return

    clean_db = db_value.lower().replace("db", "").strip()
    current_volume = f"{clean_db}dB"
    await ctx.send(f"🎚️ Đã tăng mức Decibel lên: `{clean_db} dB`.")
    if voice_client and voice_client.is_connected() and voice_client.is_playing():
        await reload_audio(ctx)

@bot.command(name="listmusic")
async def list_music(ctx):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    
    extensions = ('.mp3', '.wav', '.m4a', '.ogg')
    files = [f for f in os.listdir('.') if f.lower().endswith(extensions) and os.path.isfile(f)]
    
    if not files:
        await ctx.send("📁 Thư mục hiện tại không có tệp tin âm thanh nào hợp lệ.")
        return
        
    music_list = "\n".join([f"- `{f}`" for f in files])
    await ctx.send(f"**📁 Danh sách file nhạc có sẵn để phát:**\n{music_list}")

@bot.command(name="addadmin")
async def add_admin(ctx, user_id: int):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx): return
    admin_ids.add(user_id)
    await ctx.send(f"✅ Cấp quyền thành công cho ID: `{user_id}`.")

@bot.command(name="deladmin")
async def del_admin(ctx, user_id: int):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx): return
    if user_id in admin_ids:
        admin_ids.remove(user_id)
        await ctx.send(f"❌ Đã gỡ quyền quản trị viên của ID: `{user_id}`.")
    else:
        await ctx.send(f"⚠️ ID `{user_id}` hiện không có tên trong danh sách Admin.")

@bot.command(name="listadmin")
async def list_admin(ctx):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return

    embed = discord.Embed(
        title="👑 BẢNG PHÂN QUYỀN HỆ THỐNG",
        description="Danh sách ban quản trị tối cao đang nắm giữ quyền điều hành hệ thống Bot.",
        color=discord.Color.from_rgb(241, 196, 15)
    )

    if bot.user.avatar:
        embed.set_thumbnail(url=bot.user.avatar.url)

    embed.add_field(
        name="👑 CHỦ SỞ HỮU TỐI CAO (OWNER)",
        value=f"➔ Tài khoản: <@{owner_id}>\n➔ ID: `{owner_id}`",
        inline=False
    )

    if admin_ids:
        admin_list = "\n".join([f"➔ <@{uid}> (`{uid}`)" for uid in admin_ids])
    else:
        admin_list = "➔ *(Hiện tại chưa bổ nhiệm Admin nào)*"

    embed.add_field(
        name="🛡️ BAN QUẢN TRỊ VIÊN (ADMINS)",
        value=admin_list,
        inline=False
    )

    user_avatar_url = ctx.author.avatar.url if ctx.author.avatar else None
    embed.set_footer(
        text=f"Yêu cầu kiểm tra bởi: {ctx.author.name}",
        icon_url=user_avatar_url
    )

    await ctx.send(embed=embed)

@bot.command(name="status")
async def change_status(ctx, *, text: str):
    if not is_authorized(ctx):
        await ctx.send("❌ Bạn không có quyền sử dụng lệnh này")
        return
    if not is_owner(ctx):
        await ctx.send("❌ Lệnh này yêu cầu đặc quyền tối cao của Owner.")
        return
    
    try:
        await bot.change_presence(activity=discord.Game(name=text))
        await ctx.send(f"✅ [Owner] Đã đổi trạng thái hoạt động của Bot thành: **Đang chơi {text}**")
    except Exception as e:
        await ctx.send(f"❌ Thất bại khi cập nhật trạng thái: {e}")

BOT_TOKEN = "MTQzNjczOTk4Mzg5MjI4NzUwOA.G4IGp8.4HJNo_It2R6eZfr2BIhnTcfpwvmKD1AO-IF5Qg"
bot.run(BOT_TOKEN)
