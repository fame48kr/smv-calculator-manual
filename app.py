"""CM Calculator — Manual Category Selection"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from data_loader import load_data, search_similar_styles, get_style_processes, build_process_index, get_proc_features, STYLE_ALIAS
from image_extractor import load_image_index, get_image, get_image_by_style

ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(ENV_PATH)

st.set_page_config(page_title="CM Assistant", page_icon="✂️", layout="wide")

# ── Access control ────────────────────────────────────────────────
_APP_PASSWORD = st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") else os.environ.get("APP_PASSWORD", "")

if _APP_PASSWORD:
    if not st.session_state.get("_authenticated"):
        st.title("✂️ CM Calculator")
        st.markdown("### Please enter the access password")
        _pwd_input = st.text_input("Password", type="password", key="_pwd_input")
        if st.button("Login", type="primary"):
            if _pwd_input == _APP_PASSWORD:
                st.session_state["_authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")
        st.stop()

st.title("✂️ CM Assistant")
st.caption("Select Gender / Category → Find Similar Styles → Calculate CM")

# Load data
df_list, df_smv, df_proc, df_cat = load_data()
load_image_index()

def get_style_image(style_str: str):
    return get_image_by_style(style_str, df_list)

# ── Category option helpers ───────────────────────────────────────
CAT2_BY_CAT1 = {
    "A-A) TOP - T SHIRTS":        ["A) Crew Neck","B) V-Neck","C) POLO","D) Henley Neck","E) SQUARE Neck","F) Mock Neck"],
    "A-B) TOP - PULL OVER":       ["A) HOODED","B) Crew neck","C) POLO","D) Turtle neck","E) Funnel neck","F) V-Neck","G) Other Shape"],
    "A-C) TOP - JACKET":          ["A) Open Center Front with Hood (ZIPPER)","B) Open Center front(*ZIPPER)","C) Open center front (*BUTTON)","D) Other Shape"],
    "A-D) TOP - TANK":            ["A) TANK"],
    "A-F) TOP - ROMPER":          ["A) Sleeve less","B) Short Sleeve","C) Long Sleeve"],
    "A-G) TOP - Sports Bra":      ["A) Sports Bra Molded","B) Sports Bra Non-Molded"],
    "A-H) TOP - BODYSUIT":        ["A) Body Suit","B) HOODED ONE PIECE","C) QUARTER ZIPPER ONE PIECE","D) ONE PIECE BUBBLE JERSEY","E) ONE PIECE WITH COLLAR"],
    "A-I) TOP - CARDIGAN":        ["A) WITH COLLAR","B) WITH HOOD","C) Other Shape"],
    "A-J) TOP - SWIM COVER UP":   ["A) Long sleeve","B) Short sleeve"],
    "A-K) TOP - CAMI":            ["A) CAMI"],
    "A-L) TOP - JUMPSUIT":        ["A) JUMPSUIT"],
    "A-M) TOP - Union Suit":      ["A) Union Suit"],
    "A-N) TOP - VEST":            ["A) BOYS/ GIRLS/NEWBORN","B) MENS / WOMENS"],
    "B-A) BOTTOM - PANTS":        ["A) Long Pants","B) Short Pants"],
    "B-B) BOTTOM - LEGGINGS":     ["A) Long","B) Short"],
    "B-C) BOTTOM - SKIRTS":       ["A) Skirts"],
    "B-D) BOTTOM - LEGGINGS (ODRAMPU)": ["A) Long","B) Short"],
    "B-E) BOTTOM - DIAPER":       ["A) DIAPER"],
    "B-F) BOTTOM - JEGGING":      ["A) JEGGING"],
    "C-A) TOP - DRESS":           ["A) Long","B) Short"],
    "D-A) PAJAMA(*SLEEP WEAR)":   ["A) TOP","B) Bottom"],
    "E) OTHER":                   ["A) OTHER"],
    "F) Trunk":                   ["A) Trunk"],
}

def get_cat3_options(df, sel_cat1, sel_cat2):
    """Return sorted Cat3 options from actual data filtered by Cat1/Cat2."""
    tmp = df.copy()
    if sel_cat1:
        mask = pd.Series(False, index=tmp.index)
        for c1 in sel_cat1:
            mask |= tmp['CAT1'].str.contains(c1, na=False, case=False, regex=False)
        tmp = tmp[mask]
    if sel_cat2:
        mask = pd.Series(False, index=tmp.index)
        for c2 in sel_cat2:
            kw = c2.split(')')[-1].strip() if ')' in c2 else c2
            mask |= tmp['CAT2'].str.contains(kw, na=False, case=False, regex=False)
        tmp = tmp[mask]
    opts = sorted([v for v in tmp['CAT3'].dropna().astype(str).str.strip().unique()
                   if v.lower() not in ('nan', 'none', '')])
    return opts


# ══════════════════════════════════════════════
# STEP 1: Manual Category Selection
# ══════════════════════════════════════════════
st.header("① Style Information")

col_left, col_right = st.columns([1, 1])

with col_left:
    gender_options = sorted([
        g for g in df_list['GENDER'].dropna().astype(str).str.strip().str.title().unique()
        if g.lower() not in ('nan', 'none', '')
    ])
    genders = st.multiselect(
        "Gender",
        gender_options,
        default=[],
        help="Leave empty to search all genders."
    )

with col_right:
    cat1_options = list(CAT2_BY_CAT1.keys())
    sel_cat1 = st.multiselect("Category #1", cat1_options, default=[], key="sel_cat1")

    cat2_opts = []
    for c1 in (sel_cat1 or cat1_options):
        for c2 in CAT2_BY_CAT1.get(c1, []):
            if c2 not in cat2_opts:
                cat2_opts.append(c2)
    sel_cat2 = st.multiselect("Category #2", cat2_opts, default=[], key="sel_cat2")

    cat3_opts = get_cat3_options(df_list, sel_cat1, sel_cat2)
    sel_cat3 = st.multiselect("Category #3 (optional)", cat3_opts, default=[], key="sel_cat3")

detail_kw = st.text_input(
    "🔖 Detail Keyword (optional, comma-separated)",
    placeholder="e.g.: zipper, pocket, collar, raglan",
    help="Styles with matching construction detail tags will be shown first.",
    key="detail_kw"
)

search_btn = st.button("🔍 Search Similar Styles", type="primary")

if search_btn:
    st.session_state['search_done'] = True
    st.session_state['_genders']    = genders
    st.session_state['_sel_cat1']   = sel_cat1
    st.session_state['_sel_cat2']   = sel_cat2
    st.session_state['_sel_cat3']   = sel_cat3
    st.session_state['_detail_kw']  = detail_kw

if not st.session_state.get('search_done'):
    st.info("Select Gender and Category, then click **Search Similar Styles**.")
    st.stop()

# Use session-state-cached selections for the rest of the page
genders  = st.session_state.get('_genders', genders)
sel_cat1 = st.session_state.get('_sel_cat1', sel_cat1)
sel_cat2 = st.session_state.get('_sel_cat2', sel_cat2)
sel_cat3 = st.session_state.get('_sel_cat3', sel_cat3)


# ══════════════════════════════════════════════
# STEP 2: Similar Style Search
# ══════════════════════════════════════════════
_sec2_open = st.session_state.get('sec2_open', True)
_h2, _b2 = st.columns([9, 1])
with _h2:
    st.header("② Similar Style Search")
with _b2:
    st.write("")
    if st.button("▲ Collapse" if _sec2_open else "▼ Expand", key="sec2_btn"):
        st.session_state['sec2_open'] = not _sec2_open
        st.rerun()

use_cat2   = st.session_state.get('_f_use_cat2', True)
use_cat3   = st.session_state.get('_f_use_cat3', True)
use_gender = st.session_state.get('_f_use_gender', True)
keyword    = st.session_state.get('_f_keyword', '')

if _sec2_open:
    with st.expander("Adjust Search Filters", expanded=False):
        use_cat2   = st.checkbox("Apply Category #2 filter", value=use_cat2,   key='_f_use_cat2')
        use_cat3   = st.checkbox("Apply Category #3 filter", value=use_cat3,   key='_f_use_cat3')
        use_gender = st.checkbox("Apply Gender filter",       value=use_gender, key='_f_use_gender')
        keyword    = st.text_input("Additional keyword (optional)", value=keyword, key='_f_keyword')

sel_genders    = genders if use_gender else []
_cat2_filter   = sel_cat2 if (use_cat2 and sel_cat2) else None
_cat3_filter   = sel_cat3 if (use_cat3 and sel_cat3) else None

results = search_similar_styles(
    df_list, df_smv,
    cat1=sel_cat1 or None,
    cat2=_cat2_filter,
    cat3=_cat3_filter,
    genders=sel_genders if sel_genders else None,
    keyword=keyword,
    top_n=50,
    df_proc=df_proc,
)

# Auto-fallback: Cat3 → Cat2 only → Cat1 only
fallback_msg = None
if results.empty and _cat3_filter:
    results = search_similar_styles(
        df_list, df_smv,
        cat1=sel_cat1 or None,
        cat2=_cat2_filter,
        cat3=None,
        genders=sel_genders if sel_genders else None,
        keyword=keyword,
        top_n=50,
        df_proc=df_proc,
    )
    if not results.empty:
        fallback_msg = f"No results for Category #3 → **Searching by Category #1/2 only** ({len(results)} results)"

if results.empty and _cat2_filter:
    results = search_similar_styles(
        df_list, df_smv,
        cat1=sel_cat1 or None,
        cat2=None,
        cat3=None,
        genders=sel_genders if sel_genders else None,
        keyword=keyword,
        top_n=50,
        df_proc=df_proc,
    )
    if not results.empty:
        fallback_msg = f"No results for Category #2 → **Searching by Category #1 only** ({len(results)} results)"

if results.empty:
    st.warning("No results found. Try adjusting the category or keyword.")
    st.stop()

# ── Detail keyword prioritization ────────────────────────────────
_detail_kw = st.session_state.get('_detail_kw', '')
_detail_kws = [k.strip().lower() for k in _detail_kw.split(',') if k.strip()] if _detail_kw else []

if _detail_kws:
    _pri_idx = build_process_index(df_proc)
    def _detail_score(style_str):
        pf = get_proc_features(STYLE_ALIAS.get(str(style_str).strip(), str(style_str).strip()), _pri_idx)
        details = [d.lower() for d in pf.get('details', [])]
        return sum(1 for kw in _detail_kws if any(kw in d for d in details))
    results = results.copy()
    results['_kw_score'] = results['STYLE'].apply(_detail_score)
    results = results.sort_values('_kw_score', ascending=False).drop(columns='_kw_score').reset_index(drop=True)

_cat1_label = ', '.join(sel_cat1) if sel_cat1 else 'All'
_cat2_label = ', '.join(sel_cat2) if (use_cat2 and sel_cat2) else 'All'
_cat3_label = ', '.join(sel_cat3) if (use_cat3 and sel_cat3) else 'All'

if fallback_msg:
    st.warning(fallback_msg)
else:
    gender_label = ', '.join(sel_genders) if sel_genders else 'All genders'
    st.success(f"**{len(results)} similar styles** found — `{_cat1_label}` / `{_cat2_label}` / `{_cat3_label}` / {gender_label}")

candidates = []
for _, row in results.iterrows():
    orig_idx = row.get('ORIG_IDX', -1)
    smv_val  = row.get('TOTAL_SMV', None)
    candidates.append({
        'style':    str(row.get('STYLE', '')),
        'orig_idx': orig_idx,
        'cat2':     str(row.get('CAT2', '')),
        'cat3':     str(row.get('CAT3', '')),
        'smv':      float(smv_val) if isinstance(smv_val, float) else None,
        'brand':    str(row.get('BRAND', '')),
        'gender':   str(row.get('GENDER', '')),
    })

if not _sec2_open:
    st.caption(f"▼ {len(results)} styles found — click ▼ Expand to show")

if "selected_style" not in st.session_state:
    st.session_state.selected_style = candidates[0]['style'] if candidates else ""

if _sec2_open:
    _grid_proc_index = build_process_index(df_proc)

    COLS_PER_ROW = 8
    for row_start in range(0, len(candidates), COLS_PER_ROW):
        cols = st.columns(COLS_PER_ROW)
        for ci, c in enumerate(candidates[row_start: row_start + COLS_PER_ROW]):
            with cols[ci]:
                img = c.get('img_bytes') or get_image(c.get('orig_idx', -1))
                if img:
                    st.image(img, use_container_width=True)
                else:
                    st.markdown("🖼️ *No image*")

                smv_str = f"  SMV {c['smv']:.2f}" if c.get('smv') else ""
                st.caption(f"**{c['style']}**  \n{c['cat2']} {c['cat3']}{smv_str}")

                _lookup = STYLE_ALIAS.get(c['style'], c['style'])
                pf = get_proc_features(_lookup, _grid_proc_index, garment_type='top')
                details = pf.get('details', [])
                if details:
                    if _detail_kws:
                        tagged = []
                        for d in details:
                            if any(kw in d.lower() for kw in _detail_kws):
                                tagged.append(f"**:red[{d}]**")
                            else:
                                tagged.append(d)
                        st.caption("📌 " + " · ".join(tagged))
                    else:
                        st.caption("📌 " + " · ".join(details))

                is_selected = (st.session_state.selected_style == c['style'])
                btn_label = "✅ Selected" if is_selected else "Select"
                if st.button(btn_label, key=f"sel_{c['style']}_{row_start}_{ci}", disabled=is_selected):
                    st.session_state.selected_style = c['style']
                    st.rerun()

    st.info(f"Selected style: **{st.session_state.selected_style}**")

selected_style = st.session_state.selected_style


# ══════════════════════════════════════════════
# STEP 3: Process Adjustment
# ══════════════════════════════════════════════
_sec3_open = st.session_state.get('sec3_open', True)
_h3, _b3 = st.columns([9, 1])
with _h3:
    st.header("③ Process Adjustment")
with _b3:
    st.write("")
    if st.button("▲ Collapse" if _sec3_open else "▼ Expand", key="sec3_btn"):
        st.session_state['sec3_open'] = not _sec3_open
        st.rerun()

if not _sec3_open:
    st.caption(f"▼ Base style: {selected_style} — click ▼ Expand to show")

_proc_lookup_style = STYLE_ALIAS.get(str(selected_style).strip(), selected_style)
df_selected_proc = get_style_processes(df_proc, _proc_lookup_style, df_smv=df_smv)
ref_smv_row = results[results['STYLE'].astype(str) == str(selected_style)]
ref_total_smv = float(ref_smv_row['TOTAL_SMV'].values[0]) if len(ref_smv_row) and 'TOTAL_SMV' in ref_smv_row else 0.0

if "proc_worksheet" not in st.session_state or st.session_state.get("ws_base") != selected_style:
    base_procs = df_selected_proc[['PROCESS','MACHINE','SMV']].copy() if not df_selected_proc.empty else pd.DataFrame(columns=['PROCESS','MACHINE','SMV'])
    base_procs['SOURCE'] = selected_style
    base_procs['INCLUDE'] = True
    st.session_state.proc_worksheet = base_procs.reset_index(drop=True)
    st.session_state.ws_base = selected_style

if _sec3_open:
    if _proc_lookup_style != selected_style:
        st.info(f"ℹ️ **{selected_style}** → using process data from **{_proc_lookup_style}** (alias)")
    if df_selected_proc.empty:
        st.info(f"No process data found for '{selected_style}'. Search below to add processes.")

    tab1, tab2, tab3 = st.tabs(["📋 Process Worksheet", "➕ Add Process (Keyword Search)", "🔄 Replace Process (Style Search)"])

    with tab1:
        st.caption(f"Base: **{selected_style}** | Uncheck to exclude a process | SMV values are editable")
        ws = st.session_state.proc_worksheet
        edited_ws = st.data_editor(
            ws,
            column_config={
                "INCLUDE": st.column_config.CheckboxColumn("Include", width="small"),
                "PROCESS": st.column_config.TextColumn("Process", width="large"),
                "MACHINE": st.column_config.TextColumn("Machine", width="small"),
                "SMV":     st.column_config.NumberColumn("SMV", format="%.4f", min_value=0.0),
                "SOURCE":  st.column_config.TextColumn("Source Style", width="small"),
            },
            use_container_width=True, hide_index=True, height=400, key="ws_editor"
        )
        st.session_state.proc_worksheet = edited_ws

    with tab2:
        st.markdown("**Search processes by keyword from other styles → add selected processes to worksheet**")
        kw_col1, kw_col2 = st.columns([3, 1])
        with kw_col1:
            proc_keyword = st.text_input("Process keyword (comma-separated for multiple)", placeholder="e.g.: dorito, split hem  or  bottomband, coverstitch")
        with kw_col2:
            kw_logic = st.radio("Search condition", ["OR", "AND"], horizontal=True, key="kw_logic",
                                help="OR: match any keyword / AND: match all keywords")

        if proc_keyword:
            keywords = [k.strip() for k in proc_keyword.split(',') if k.strip()]

            def _match(row, kws, logic):
                target = str(row['PROCESS']) + ' ' + str(row['MACHINE'])
                hits = [k.lower() in target.lower() for k in kws]
                return all(hits) if logic == "AND" else any(hits)

            mask = df_proc.apply(lambda r: _match(r, keywords, kw_logic), axis=1)
            kw_results = df_proc[mask].copy()

            if kw_results.empty:
                st.warning("No processes found for the given keyword(s).")
            else:
                styles_with_kw_raw = list(kw_results['STYLE'].unique())
                _ref_cat1 = sel_cat1[0] if sel_cat1 else ''
                _ref_prefix = str(_ref_cat1)[:3].upper()
                _cat1_lookup = df_list.drop_duplicates('STYLE').set_index('STYLE')['CAT1'].to_dict() if 'CAT1' in df_list.columns else {}

                def _cat_priority(sname):
                    cat = str(_cat1_lookup.get(sname, '')).strip()
                    if cat == _ref_cat1: return 0
                    if cat[:3].upper() == _ref_prefix[:3]: return 1
                    return 2

                styles_with_kw = sorted(styles_with_kw_raw, key=_cat_priority)
                st.success(f"**{len(kw_results)} processes** found — {len(styles_with_kw)} styles  |  sorted by category relevance")
                if _ref_cat1:
                    st.caption(f"Priority: 🥇 Same CAT1 ({_ref_cat1[:6]}…) → 🥈 Same category group → 🥉 Other")

                st.markdown("**Select a style:**")
                GCOLS = 8
                for rs in range(0, min(len(styles_with_kw), 24), GCOLS):
                    gcols = st.columns(GCOLS)
                    for gi, sname in enumerate(styles_with_kw[rs:rs+GCOLS]):
                        with gcols[gi]:
                            img = get_style_image(sname)
                            if img:
                                st.image(img, use_container_width=True)
                            else:
                                st.markdown("🖼️")
                            match_cnt = len(kw_results[kw_results['STYLE']==sname])
                            total_cnt = len(df_proc[df_proc['STYLE'].astype(str).str.strip()==sname])
                            _scat = str(_cat1_lookup.get(sname, '')).strip()
                            _badge = "🥇" if _scat == _ref_cat1 else ("🥈" if _scat[:3].upper() == _ref_prefix[:3] else "🥉")
                            st.caption(f"{_badge} **{sname}**  \n🔍{match_cnt} / {total_cnt} proc")
                            is_sel = st.session_state.get("kw_style_sel") == sname
                            if st.button("Select" if not is_sel else "✅", key=f"kw_img_{sname}_{rs}_{gi}", disabled=is_sel):
                                st.session_state["kw_style_sel"] = sname
                                st.rerun()

                sel_src_style = st.session_state.get("kw_style_sel", styles_with_kw[0])
                if sel_src_style not in styles_with_kw:
                    sel_src_style = styles_with_kw[0]

                all_style_procs = df_proc[df_proc['STYLE'].astype(str).str.strip() == sel_src_style].copy()
                matched_nos = set(kw_results[kw_results['STYLE'] == sel_src_style].index)
                all_style_procs['🔍'] = all_style_procs.index.map(lambda i: "★ match" if i in matched_nos else "")
                avail = [c for c in ['PROCESS','MACHINE','SMV'] if c in all_style_procs.columns]
                style_procs_disp = all_style_procs[['🔍'] + avail].assign(ADD=False)
                match_count = len(matched_nos)
                total_count = len(all_style_procs)
                st.info(f"**{sel_src_style}** — {total_count} processes total  |  🔍 **{match_count}** match keyword  |  ★ = keyword match row")

                edited_kw = st.data_editor(
                    style_procs_disp,
                    column_config={
                        "ADD": st.column_config.CheckboxColumn("Add", width="small"),
                        "🔍":  st.column_config.TextColumn("🔍", width="small"),
                    },
                    use_container_width=True, hide_index=True, height=400, key="kw_editor",
                    disabled=["🔍", "PROCESS", "MACHINE", "SMV"],
                )
                to_add = edited_kw[edited_kw['ADD'] == True]
                st.caption(f"Selected processes SMV total: **{to_add['SMV'].sum():.4f}** min ({len(to_add)} processes)")

                if st.button("➕ Add Selected Processes to Worksheet", type="primary", key="add_procs_btn"):
                    if not to_add.empty:
                        new_rows = to_add[avail].copy()
                        new_rows['SOURCE'] = sel_src_style
                        new_rows['INCLUDE'] = True
                        existing = st.session_state.proc_worksheet
                        st.session_state.proc_worksheet = pd.concat([existing, new_rows], ignore_index=True)
                        st.success(f"{len(new_rows)} process(es) added!")
                        st.rerun()

    with tab3:
        st.markdown("**Replace Process:** Select processes to remove from worksheet → replace with processes from another style")
        ws_cur = st.session_state.proc_worksheet
        st.markdown("**① Select processes to remove from worksheet**")
        ws_check = ws_cur.copy()
        ws_check['REMOVE'] = False
        edited_remove = st.data_editor(
            ws_check[['REMOVE','PROCESS','MACHINE','SMV','SOURCE']],
            column_config={"REMOVE": st.column_config.CheckboxColumn("Remove", width="small")},
            use_container_width=True, hide_index=True, height=250, key="remove_editor"
        )
        to_remove_idx = edited_remove[edited_remove['REMOVE'] == True].index.tolist()

        st.markdown("**② Search for replacement processes by style**")
        rep_col1, rep_col2, rep_col3 = st.columns([2, 3, 1])
        with rep_col1:
            rep_style_kw = st.text_input("Style number", placeholder="e.g.: 625386, D44356")
        with rep_col2:
            rep_proc_kw = st.text_input("Process keyword (comma-separated)", placeholder="e.g.: bottomband, hem  or  join, coverstitch")
        with rep_col3:
            rep_logic = st.radio("Condition", ["OR", "AND"], horizontal=True, key="rep_logic",
                                 help="OR: any / AND: all")

        if rep_style_kw:
            rep_proc_df = df_proc[
                df_proc['STYLE'].astype(str).str.contains(rep_style_kw, case=False, na=False, regex=False)
            ].copy()
            if rep_proc_kw:
                rep_keywords = [k.strip() for k in rep_proc_kw.split(',') if k.strip()]
                def _rep_match(row, kws, logic):
                    target = str(row['PROCESS']) + ' ' + str(row['MACHINE'])
                    hits = [k.lower() in target.lower() for k in kws]
                    return all(hits) if logic == "AND" else any(hits)
                rep_mask = rep_proc_df.apply(lambda r: _rep_match(r, rep_keywords, rep_logic), axis=1)
                rep_proc_df = rep_proc_df[rep_mask]

            if rep_proc_df.empty:
                st.warning("No results found.")
            else:
                rep_styles = [str(s) for s in rep_proc_df['STYLE'].unique()]
                img_col, info_col = st.columns([1, 3])
                with img_col:
                    rep_img = get_style_image(rep_styles[0])
                    if rep_img:
                        st.image(rep_img, caption=rep_styles[0], use_container_width=True)
                    else:
                        st.markdown(f"🖼️ *No image*  \n**{rep_styles[0]}**")
                with info_col:
                    st.success(f"**{len(rep_proc_df)} processes** found — Style(s): {', '.join(rep_styles[:3])}")
                avail_r = [c for c in ['PROCESS','MACHINE','SMV'] if c in rep_proc_df.columns]
                rep_disp = rep_proc_df[avail_r].assign(ADD=False)
                edited_rep = st.data_editor(
                    rep_disp,
                    column_config={"ADD": st.column_config.CheckboxColumn("Add", width="small")},
                    use_container_width=True, hide_index=True, height=250, key="rep_editor"
                )
                to_rep_add = edited_rep[edited_rep['ADD'] == True]
                st.caption(f"Processes to add SMV: **{to_rep_add['SMV'].sum():.4f}** min ({len(to_rep_add)}) | Processes to remove: {len(to_remove_idx)}")

                if st.button("🔄 Replace (Remove → Add)", type="primary", key="replace_btn"):
                    ws_updated = st.session_state.proc_worksheet.drop(index=to_remove_idx).reset_index(drop=True)
                    if not to_rep_add.empty:
                        new_rows = to_rep_add[avail_r].copy()
                        new_rows['SOURCE'] = rep_style_kw
                        new_rows['INCLUDE'] = True
                        ws_updated = pd.concat([ws_updated, new_rows], ignore_index=True)
                    st.session_state.proc_worksheet = ws_updated
                    st.success(f"Replacement complete: {len(to_remove_idx)} removed → {len(to_rep_add)} added")
                    st.rerun()

# SMV Summary
final_ws = st.session_state.proc_worksheet
included = final_ws[final_ws['INCLUDE'] == True]
current_smv = float(included['SMV'].sum()) if not included.empty else 0.0

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Included Processes", f"{len(included)}")
c2.metric("Excluded Processes", f"{len(final_ws) - len(included)}")
c3.metric("Process Analysis SMV", f"{current_smv:.4f} min")

