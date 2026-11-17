"""쇼핑리스트 앱 (Streamlit)

PRD.md 기준. 3단계: UI 디자인.
"""

import html
import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st

# ============================================================
# 상수
# ============================================================
DATA_FILE = Path(__file__).parent / "shopping_list.json"
MAX_NAME_LENGTH = 50
MIN_QUANTITY = 1
MAX_QUANTITY = 99


# ============================================================
# 데이터 모델
# ============================================================
def new_item(name: str, quantity: int = 1) -> dict:
    """PRD 4장 데이터 모델에 맞는 아이템 딕셔너리를 만든다.

    {id, name, quantity, checked, created_at}
    """
    return {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "quantity": quantity,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }


# ============================================================
# 데이터 함수 (파일 저장 / 불러오기)
# ============================================================
def load_items() -> list[dict]:
    """shopping_list.json에서 아이템 목록을 불러온다.

    파일이 없거나 JSON이 깨졌거나 형식이 리스트가 아니면 빈 리스트를 반환한다.
    """
    if not DATA_FILE.exists():
        return []
    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def save_items(items: list[dict]) -> None:
    """아이템 목록을 shopping_list.json에 저장한다."""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# ============================================================
# 검증 / 헬퍼
# ============================================================
def clean_name(name: str | None) -> str | None:
    """이름 앞뒤 공백을 제거하고 50자로 자른다. 비어 있으면 None."""
    name = (name or "").strip()
    return name[:MAX_NAME_LENGTH] if name else None


def clamp_quantity(quantity) -> int:
    """수량을 1~99 범위의 정수로 맞춘다."""
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        return MIN_QUANTITY
    return max(MIN_QUANTITY, min(MAX_QUANTITY, quantity))


def find_item(item_id: str) -> dict | None:
    """id로 아이템을 찾는다."""
    for item in st.session_state["items"]:
        if item.get("id") == item_id:
            return item
    return None


def escape_md(text: str) -> str:
    """사용자 입력이 마크다운 문법으로 해석되지 않도록 특수문자를 이스케이프한다."""
    specials = "\\`*_{}[]()#+-.!~|<>:$"
    return "".join("\\" + ch if ch in specials else ch for ch in text)


def flash(message: str) -> None:
    """다음 화면 그리기 때 보여줄 경고 메시지를 저장한다."""
    st.session_state["flash"] = message


# ============================================================
# 아이템 조작 함수
# ============================================================
def add_item(name: str, quantity: int) -> bool:
    """새 아이템을 목록에 추가하고 저장한다. (F1) 성공 여부를 반환."""
    name = clean_name(name)
    if name is None:
        return False
    st.session_state["items"].append(new_item(name, clamp_quantity(quantity)))
    save_items(st.session_state["items"])
    return True


def update_item(item_id: str, name: str, quantity: int) -> bool:
    """아이템의 이름과 수량을 수정하고 저장한다. (F2) 성공 여부를 반환."""
    name = clean_name(name)
    item = find_item(item_id)
    if name is None or item is None:
        return False
    item["name"] = name
    item["quantity"] = clamp_quantity(quantity)
    save_items(st.session_state["items"])
    return True


def delete_item(item_id: str) -> None:
    """아이템을 삭제하고 저장한다. (F3)"""
    st.session_state["items"] = [
        item for item in st.session_state["items"] if item.get("id") != item_id
    ]
    if st.session_state["editing_id"] == item_id:
        st.session_state["editing_id"] = None
    save_items(st.session_state["items"])


def toggle_item(item_id: str) -> None:
    """아이템의 체크(구매 완료) 상태를 바꾸고 저장한다. (F4)"""
    item = find_item(item_id)
    if item is None:
        return
    item["checked"] = not item.get("checked", False)
    save_items(st.session_state["items"])


def clear_checked() -> None:
    """체크된 아이템을 모두 삭제하고 저장한다. (F3 부가 기능)"""
    st.session_state["items"] = [
        item for item in st.session_state["items"] if not item.get("checked")
    ]
    if find_item(st.session_state["editing_id"] or "") is None:
        st.session_state["editing_id"] = None
    save_items(st.session_state["items"])


# ============================================================
# 버튼 콜백 (클릭 한 번에 바로 반영되도록 on_click / on_change 사용)
# ============================================================
def on_add() -> None:
    if not add_item(st.session_state.get("new_name"), st.session_state.get("new_qty")):
        flash("아이템 이름을 입력해 주세요.")


def on_start_edit(item_id: str) -> None:
    # 이전에 입력하다 만 값이 남지 않도록 수정용 위젯 상태를 비운다
    st.session_state.pop(f"edit_name_{item_id}", None)
    st.session_state.pop(f"edit_qty_{item_id}", None)
    st.session_state["editing_id"] = item_id


def on_save_edit(item_id: str) -> None:
    ok = update_item(
        item_id,
        st.session_state.get(f"edit_name_{item_id}"),
        st.session_state.get(f"edit_qty_{item_id}"),
    )
    if ok:
        st.session_state["editing_id"] = None
    else:
        flash("아이템 이름은 비워 둘 수 없어요.")


def on_cancel_edit() -> None:
    st.session_state["editing_id"] = None


# ============================================================
# 상태 초기화
# ============================================================
def init_state() -> None:
    """세션 상태를 처음 한 번만 초기화한다."""
    if "items" not in st.session_state:
        st.session_state["items"] = load_items()
    if "editing_id" not in st.session_state:
        st.session_state["editing_id"] = None


# ============================================================
# 화면 - 스타일
# ============================================================
FILTERS = ["전체", "남은 항목", "완료 항목"]

# 색은 투명도(opacity / rgba)와 테마 변수 위주로 지정해서 라이트·다크 모드 모두 잘 보이게 한다.
CUSTOM_CSS = """
<style>
/* 본문 폭을 살짝 좁혀 휴대폰 앱 느낌으로 */
.block-container { max-width: 640px; padding-top: 2.5rem; padding-bottom: 4rem; }

/* 헤더 */
div.app-title { font-size: 2.1rem; font-weight: 800; line-height: 1.3; margin: 0 0 .25rem 0; }
div.app-sub { opacity: .65; font-size: .95rem; margin-bottom: .5rem; }

/* 아이템 이름 */
.item-name { font-size: 1.05rem; line-height: 1.4; word-break: break-all; }
.item-qty {
  display: inline-block; margin-left: .4rem; padding: 0 .45rem;
  border-radius: 999px; font-size: .8rem; font-weight: 600;
  background: rgba(46, 158, 91, .15); color: #2E9E5B;
}
.item-name.done { text-decoration: line-through; opacity: .45; }
.item-name.done .item-qty { background: rgba(128, 128, 128, .15); color: inherit; }

/* 휴대폰에서도 아이템 행·입력 줄이 세로로 쪼개지지 않게 한 줄 유지 */
[class*="st-key-row_"] [data-testid="stHorizontalBlock"],
.st-key-add_row [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .5rem; }
[class*="st-key-row_"] [data-testid="stColumn"],
.st-key-add_row [data-testid="stColumn"] { min-width: 0 !important; }

/* 아이템 카드 여백을 줄여 한 화면에 더 많이 보이게 */
[class*="st-key-row_"] { padding: .35rem .75rem !important; }

/* 손가락으로 누르기 쉬운 아이콘 버튼 */
[class*="st-key-row_"] button { min-height: 2.5rem; min-width: 2.5rem; padding: 0 .4rem; }

/* 수정 중인 행 강조 */
[class*="st-key-editing_"] {
  border: 2px solid #2E9E5B !important;
  background: rgba(46, 158, 91, .07);
}

/* 빈 리스트 안내 */
.empty-box { text-align: center; padding: 2.5rem 1rem; opacity: .7; }
.empty-box .emoji { font-size: 3rem; }
</style>
"""


def item_label_html(item: dict) -> str:
    """아이템 이름 + 수량 뱃지 HTML. 사용자 입력은 반드시 이스케이프한다."""
    # html.escape로 HTML 주입을 막고, escape_md로 마크다운 해석을 막는다.
    name = escape_md(html.escape(item["name"], quote=False))
    qty = clamp_quantity(item.get("quantity"))
    done = " done" if item.get("checked") else ""
    return f'<span class="item-name{done}">{name}<span class="item-qty">x{qty}</span></span>'


# ============================================================
# 화면 - 구성 요소
# ============================================================
def render_header(items: list[dict]) -> None:
    """상단 헤더: 제목 + 진행 바 + n / m 완료 (F4)."""
    st.markdown('<div class="app-title">🛒 쇼핑리스트</div>', unsafe_allow_html=True)
    total = len(items)
    done = sum(1 for item in items if item.get("checked"))
    if not total:
        st.markdown('<div class="app-sub">오늘 살 것을 적어 보세요</div>', unsafe_allow_html=True)
        return
    st.progress(done / total, text=f"**{done} / {total}** 완료")
    if done == total:
        st.success("🎉 장보기 완료!")


def render_add_form() -> None:
    """F1: 아이템 추가 폼 (이름 넓게 / 수량·버튼 좁게 한 줄)."""
    with st.form("add_form", clear_on_submit=True, border=False):
        with st.container(key="add_row"):
            col_name, col_qty, col_btn = st.columns([6, 3, 2], vertical_alignment="bottom")
            col_name.text_input(
                "아이템 이름", key="new_name", max_chars=MAX_NAME_LENGTH,
                placeholder="예: 우유, 계란, 식빵", label_visibility="collapsed",
            )
            col_qty.number_input(
                "수량", key="new_qty", min_value=MIN_QUANTITY, max_value=MAX_QUANTITY,
                value=1, step=1, label_visibility="collapsed",
            )
            col_btn.form_submit_button(
                "추가", on_click=on_add, type="primary", use_container_width=True,
            )


def render_item_row(item: dict) -> None:
    """아이템 한 줄. 수정 중이면 입력칸, 아니면 [체크 | 이름 x수량 | ✏️ | 🗑️]."""
    item_id = item["id"]

    if st.session_state["editing_id"] == item_id:  # F2: 수정 모드
        with st.container(border=True, key=f"editing_{item_id}"):
            st.caption("✏️ 수정 중")
            col_name, col_qty = st.columns([3, 1])
            col_name.text_input(
                "이름 수정", value=item["name"], key=f"edit_name_{item_id}",
                max_chars=MAX_NAME_LENGTH, label_visibility="collapsed",
            )
            col_qty.number_input(
                "수량 수정", value=clamp_quantity(item.get("quantity")),
                min_value=MIN_QUANTITY, max_value=MAX_QUANTITY, step=1,
                key=f"edit_qty_{item_id}", label_visibility="collapsed",
            )
            col_save, col_cancel = st.columns(2)
            col_save.button(
                "저장", key=f"save_{item_id}", on_click=on_save_edit, args=(item_id,),
                type="primary", use_container_width=True,
            )
            col_cancel.button(
                "취소", key=f"cancel_{item_id}", on_click=on_cancel_edit,
                use_container_width=True,
            )
        return

    with st.container(border=True, key=f"row_{item_id}"):
        col_chk, col_name, col_edit, col_del = st.columns(
            [1, 8, 1.4, 1.4], vertical_alignment="center",
        )
        col_chk.checkbox(  # F4: 체크
            "완료", value=bool(item.get("checked")), key=f"chk_{item_id}",
            on_change=toggle_item, args=(item_id,), label_visibility="collapsed",
        )
        col_name.markdown(item_label_html(item), unsafe_allow_html=True)
        col_edit.button(
            ":material/edit:", key=f"edit_{item_id}", help="수정", type="tertiary",
            on_click=on_start_edit, args=(item_id,),
        )
        col_del.button(  # F3: 삭제
            ":material/delete:", key=f"del_{item_id}", help="삭제", type="tertiary",
            on_click=delete_item, args=(item_id,),
        )


def render_empty() -> None:
    st.markdown(
        '<div class="empty-box"><div class="emoji">🧺</div>'
        "<p>리스트가 비어 있어요.<br>아이템을 추가해 보세요!</p></div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="쇼핑리스트", page_icon="🛒", layout="centered")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_state()
    items = st.session_state["items"]

    render_header(items)
    render_add_form()

    # 콜백에서 남긴 경고 메시지 표시 (한 번만)
    if message := st.session_state.pop("flash", None):
        st.warning(message, icon="⚠️")

    if not items:
        render_empty()
        return

    # F6: 필터
    selected = st.segmented_control(
        "보기", FILTERS, key="filter", default="전체", label_visibility="collapsed",
    ) or "전체"  # 선택을 해제해도 '전체'로 취급
    if selected == "남은 항목":
        visible = [item for item in items if not item.get("checked")]
    elif selected == "완료 항목":
        visible = [item for item in items if item.get("checked")]
    else:
        visible = items

    if not visible:
        st.caption("해당하는 아이템이 없어요.")
    for item in visible:
        render_item_row(item)

    st.write("")
    st.button(  # F3 부가: 완료 항목 일괄 삭제
        "완료 항목 모두 삭제", icon=":material/delete_sweep:", on_click=clear_checked,
        disabled=not any(item.get("checked") for item in items),
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
