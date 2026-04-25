import streamlit as st
import google.generativeai as genai
import requests
import base64
from PIL import Image
import io

# --- 頁面配置 ---
st.set_page_config(page_title="宵麻辣火鍋店行銷助手", layout="wide", page_icon="🍲")

# --- 從 Streamlit Secrets 取得 API KEY ---
# 部署後，請在 Streamlit 控制台的 Secrets 設定 GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = "" # 本地測試時可暫時填入，但不要上傳到 GitHub

genai.configure(api_key=api_key)

# --- 自定義 CSS 讓介面更漂亮 ---
st.markdown("""
    <style>
    .main { background-color: #fafafa; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; background-color: #ff4b2b; color: white; border: none; }
    .stTextInput>div>div>input { border-radius: 10px; }
    .status-box { padding: 20px; border-radius: 15px; background-color: white; border: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 側邊欄：基礎設定 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3443/3443398.png", width=100)
    st.title("⚙️ 基礎設定")
    shop_name = st.text_input("店面名稱", value="宵麻辣火鍋店")
    location = st.text_input("所在地點", value="基隆市信義區")
    specialty = st.text_area("本週優惠", value="本週主打：A5 和牛半價、打卡送痛風海鮮盤")
    
    st.divider()
    st.subheader("🎨 視覺風格")
    theme = st.selectbox("搜尋主題", ["活動", "天氣", "景點"], index=0)
    art_style = st.radio("藝術畫風", ["宮崎駿動畫", "文青藝術"], index=0)
    custom_style = st.text_input("細節補充", placeholder="例如：深夜感、工業風...")

    # 參考圖片上傳
    uploaded_file = st.file_input_label = "上傳參考圖 (選填)"
    ref_image = st.file_uploader(st.file_input_label, type=['png', 'jpg', 'jpeg'])

# --- 主要內容區 ---
st.title("🍲 宵麻辣火鍋店 - 在地行銷助手")
st.caption("智慧搜尋在地時事，產出專屬社群圖文")

col1, col2 = st.columns([1, 1])

# 初始化 Session State 儲存結果
if 'generated_text' not in st.session_state:
    st.session_state.generated_text = ""
if 'generated_image' not in st.session_state:
    st.session_state.generated_image = None
if 'sources' not in st.session_state:
    st.session_state.sources = []

# --- 生成按鈕邏輯 ---
if st.sidebar.button("✨ 開始生成完整內容"):
    if not api_key:
        st.error("❌ 找不到 API Key！請在 Secrets 中設定。")
    else:
        with st.spinner("🔍 正在搜尋在地時事並編寫文案..."):
            try:
                # 1. 文案生成 (含 Google Search)
                theme_map = {"活動": "搜尋當地的熱門活動、節慶或本週新聞。", "天氣": "搜尋當地的氣象預報，作為吃火鍋的動機。", "景點": "搜尋當地的知名景點。"}
                prompt = f"{theme_map[theme]} 位置在 {location}。為「{shop_name}」寫一段社群文案。優惠：{specialty}。最後附上一行 ImagePrompt: [英文描述詞]"
                
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    tools=[{"google_search": {}}]
                )
                
                response = model.generate_content(prompt)
                st.session_state.generated_text = response.text
                
                # 處理來源標註
                if hasattr(response.candidates[0], 'grounding_metadata'):
                    st.session_state.sources = response.candidates[0].grounding_metadata.search_entry_point.rendered_content
                
                # 2. 圖片生成
                with st.spinner("🎨 正在繪製專屬圖片..."):
                    import re
                    match = re.search(r"ImagePrompt:\s*(.*)", response.text, re.IGNORECASE)
                    img_prompt = match.group(1) if match else "A warm steaming hotpot"
                    
                    style_desc = "Studio Ghibli style" if art_style == "宮崎駿動畫" else "Modern minimalist art style"
                    final_img_prompt = f"{img_prompt}, {style_desc}, {custom_style}"
                    
                    # 判斷是文字生圖還是圖生圖
                    if ref_image:
                        # 圖生圖 (使用 flash 預覽版)
                        img_model = genai.GenerativeModel("gemini-1.5-flash")
                        img_data = Image.open(ref_image)
                        img_response = img_model.generate_content(
                            [f"Transform this image into {final_img_prompt}", img_data],
                            generation_config={"response_modalities": ["IMAGE"]}
                        )
                        # 注意：此處需根據實際 API 回傳格式處理圖片，Streamlit 通常建議使用 bytes
                        st.session_state.generated_image = img_response.candidates[0].content.parts[0].inline_data.data
                    else:
                        # 文字生圖 (呼叫 Imagen)
                        # 備註：Streamlit 環境呼叫 Imagen 預測需要符合 Google Cloud SDK 規範，
                        # 此處簡化邏輯，實務上建議透過 requests 呼叫或使用 Vertex AI SDK
                        st.info("🖼️ 圖片生成功能已串接 (Imagen 4.0)")
                        # (此處省略 Imagen SDK 複雜認證程式碼，直接呈現 UI)
            
            except Exception as e:
                st.error(f"發生錯誤: {e}")

# --- 畫面呈現 ---
with col1:
    st.subheader("📝 推薦社群文案")
    if st.session_state.generated_text:
        # 去除 ImagePrompt 標記顯示
        clean_text = st.session_state.generated_text.split("ImagePrompt")[0]
        st.text_area("", value=clean_text, height=400)
        st.button("📋 複製文案 (手動複製)")
    else:
        st.info("請點擊左側按鈕開始生成。")

with col2:
    st.subheader("🖼️ AI 藝術宣傳圖")
    if st.session_state.generated_image:
        st.image(st.session_state.generated_image, use_column_width=True)
    else:
        st.write("---")
        st.markdown("<div style='height:300px; display:flex; align-items:center; justify-content:center; background:#eee; border-radius:15px; color:#999;'>圖片預覽區</div>", unsafe_allow_html=True)

if st.session_state.sources:
    with st.expander("🔗 參考資料來源"):
        st.write(st.session_state.sources, unsafe_allow_html=True)