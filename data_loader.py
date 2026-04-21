"""Data loader — reads from parquet (cloud) or Excel (local), auto-detected."""
import os
import pandas as pd
import streamlit as st

EXCEL_PATH = r"D:\업무 효율화 develop 관련\smv_calculator\2.품셈표 등록된 스타일 V2 (2026.02.13)- 수정본.xlsx"
DATA_DIR   = "data"
IS_CLOUD   = not os.path.exists(EXCEL_PATH)


@st.cache_data(show_spinner="Loading data...")
def load_data():
    if IS_CLOUD:
        return _load_from_parquet()
    return _load_from_excel()


def _load_from_parquet():
    df_list = pd.read_parquet(os.path.join(DATA_DIR, 'df_list.parquet'))
    df_smv  = pd.read_parquet(os.path.join(DATA_DIR, 'df_smv.parquet'))
    df_proc = pd.read_parquet(os.path.join(DATA_DIR, 'df_proc.parquet'))
    df_cat  = pd.read_parquet(os.path.join(DATA_DIR, 'df_cat.parquet'))
    df_list['GENDER'] = df_list['GENDER'].astype(str).str.strip().str.title()
    return df_list, df_smv, df_proc, df_cat


def _load_from_excel():
    df_list = pd.read_excel(EXCEL_PATH, sheet_name='LIST ', header=1)
    df_list.columns = [str(c).strip() for c in df_list.columns]
    df_list = df_list.rename(columns={
        '번호': 'NO', '이미지': 'IMAGE', '시즌': 'SEASON',
        '브랜드': 'BRAND', '디비젼': 'DIVISION', '공장명': 'FACTORY',
        'AGE / TYPE': 'GENDER', 'CATEGORY#1': 'CAT1', 'CATEGORY#2': 'CAT2',
        'CATEGORY#3': 'CAT3', 'CATEGORY#4': 'CAT4',
        '원단유형': 'FABRIC_TYPE', 'YDS 당 중량': 'YDS_WEIGHT',
    })
    df_list = df_list[df_list['STYLE'].notna()].reset_index(drop=False)
    df_list = df_list.rename(columns={'index': 'ORIG_IDX'})
    df_list['GENDER'] = df_list['GENDER'].astype(str).str.strip().str.title()

    df_smv = pd.read_excel(EXCEL_PATH, sheet_name='SMV_요약')
    df_smv.columns = [str(c).strip() for c in df_smv.columns]
    df_smv = df_smv.rename(columns={
        'Style#': 'STYLE', 'Gender': 'GENDER',
        'Category#1': 'CAT1', 'Category#2': 'CAT2',
        'Category#3': 'CAT3', 'Category#4': 'CAT4',
        'Total SMV(분)': 'TOTAL_SMV', '공정수': 'PROC_COUNT', '사용기계': 'MACHINES'
    })

    df_proc = pd.read_excel(EXCEL_PATH, sheet_name='yakjin_smv_style_process_popup')
    df_proc.columns = [str(c).strip() for c in df_proc.columns]
    df_proc = df_proc.rename(columns={
        'No.': 'NO', 'Style#': 'STYLE', 'Gender': 'GENDER',
        '기본공정': 'PROCESS', '기계명': 'MACHINE',
        '가로스펙(W_SPEC)': 'W_SPEC', '세로스펙(H_SPEC)': 'H_SPEC',
        '중간사이즈(M_SIZE)': 'M_SIZE',
        'Category #1': 'CAT1', 'Category #2': 'CAT2',
        'Category #3': 'CAT3', 'Category #4': 'CAT4',
        'GSD SMV': 'SMV'
    })

    df_cat_raw = pd.read_excel(EXCEL_PATH, sheet_name='카테고리', header=None)
    df_cat = df_cat_raw.iloc[1:].copy()
    df_cat.columns = ['NO', 'TYPE', 'SEQ', 'CAT1', 'CAT2', 'CAT3', 'CAT4']
    df_cat = df_cat[df_cat['CAT1'].notna()].reset_index(drop=True)

    return df_list, df_smv, df_proc, df_cat


# ── ① Process DB index ────────────────────────────────────────────
def build_process_index(df_proc: pd.DataFrame) -> dict:
    idx = {}
    for style, grp in df_proc.groupby(df_proc['STYLE'].astype(str).str.strip()):
        proc_text = ' '.join(grp['PROCESS'].fillna('').astype(str)).lower()
        mach_text = ' '.join(grp['MACHINE'].fillna('').astype(str)).lower()
        idx[style] = proc_text + ' ' + mach_text
    return idx


def get_proc_features(style: str, proc_index: dict, garment_type: str = 'top') -> dict:
    text = proc_index.get(str(style).strip(), '')
    if not text:
        return {}

    f = {}

    if any(k in text for k in ['side pocket', 'side seam pocket', 'side-seam pocket']):
        f['pocket'] = 'side-seam'
    elif any(k in text for k in ['welt pocket', 'welt']):
        f['pocket'] = 'welt'
    elif any(k in text for k in ['kangaroo', 'pouch']):
        f['pocket'] = 'kangaroo'
    elif 'patch pocket' in text:
        f['pocket'] = 'patch'
    elif 'chest pocket' in text:
        f['pocket'] = 'chest'
    elif 'pocket' in text:
        f['pocket'] = 'YES'
    else:
        f['pocket'] = 'NO'

    details = []
    if any(k in text for k in ['pocket', ' pkt', 'pkt ']):
        details.append('pocket')
    if any(k in text for k in ['collar', 'attach collar', 'sew collar', 'inner collar',
                                'join collar', 'invert collar', 'topstitch collar', 'collar band']):
        details.append('collar')
    if any(k in text for k in ['zipper', 'zip ', 'zip guard', 'invisible zip',
                                'coil zip', 'attach zip', 'topstitch zip']):
        details.append('zipper')
    if any(k in text for k in ['placket', 'plkt', 'button band', 'button placket']):
        details.append('placket')
    if any(k in text for k in ['button hole', 'buttonhole', 'attach button',
                                'sew button', 'button loop', 'bartack button']):
        details.append('button')
    if any(k in text for k in ['snap', 'attach snap', 'popper', 'press snap']):
        details.append('snap')
    if any(k in text for k in ['stud', 'attach stud', 'press stud', 'rivet']):
        details.append('stud')
    if any(k in text for k in ['eyelet', 'attach eyelet']):
        details.append('eyelet')
    if any(k in text for k in ['grommet', 'attach grommet']):
        details.append('grommet')
    if any(k in text for k in ['keyhole', 'key hole', 'attach keyhole', 'keyhole opening']):
        details.append('key hole')
    if any(k in text for k in ['o ring', 'o-ring', 'd-ring', 'ring attach', 'attach ring']):
        details.append('O-ring')
    if any(k in text for k in ['yoke', 'attach yoke', 'join yoke', 'sew yoke']):
        details.append('yoke')
    if any(k in text for k in ['strap', 'attach strap', 'sew strap', 'join strap']):
        details.append('strap')
    if any(k in text for k in ['bow', 'attach bow', 'bow tie', 'bow trim']):
        details.append('bow')
    if any(k in text for k in ['patch', 'attach patch']):
        details.append('patch')
    if any(k in text for k in ['half moon', 'halfmoon', 'half-moon']):
        details.append('half moon')
    if any(k in text for k in [' slit', 'slit ', 'side slit', 'hem slit']):
        details.append('slit')
    if any(k in text for k in ['vent', 'back vent', 'side vent']):
        details.append('vent')
    if any(k in text for k in ['pleat', 'box pleat', 'kick pleat']):
        details.append('pleats')
    if any(k in text for k in ['tuck', 'pin tuck']):
        details.append('tuck')
    if any(k in text for k in ['shirring', 'shirr', 'mobiloin', 'elasticate']):
        details.append('shirring')
    if any(k in text for k in ['smocking', 'smock']):
        details.append('smocking')
    if any(k in text for k in ['ruffle', 'frill', 'gather', 'gathered']):
        details.append('ruffle')
    if any(k in text for k in ['flag label', 'attach flag', 'flag lbl']):
        details.append('flag label')
    if any(k in text for k in ['j-stitch', 'j stitch', 'jstitch', 'j/stitch']):
        details.append('J-stitch')
    if any(k in text for k in ['drawcord', 'draw cord', 'insert cord', 'attach cord', 'thread cord']):
        details.append('drawcord')
    if any(k in text for k in ['elastic', 'insert elastic', 'attach elastic']):
        details.append('elastic')
    if any(k in text for k in ['lace', 'attach lace', 'lace trim']):
        details.append('lace')
    if any(k in text for k in ['ribbon', 'attach ribbon', 'sew ribbon', 'ribbon trim', 'ribbon tie']):
        details.append('ribbon')
    if any(k in text for k in ['tulle', 'attach tulle', 'sew tulle', 'tulle layer', 'tulle skirt']):
        details.append('tulle')
    if any(k in text for k in ['attach ear', 'sew ear', 'animal ear', 'hood ear', 'ear attachment', 'ear panel']):
        details.append('ears')
    if any(k in text for k in ['attach horn', 'sew horn', 'horn panel', 'horn attachment']):
        details.append('horn')
    if any(k in text for k in ['sherpa', 'sherpa lining', 'attach sherpa', 'sew sherpa']):
        details.append('sherpa lining')

    if details:
        f['details'] = details

    return f


# ── Style aliases ────────────────────────────────────────────────
STYLE_ALIAS: dict[str, str] = {
    '816631': 'D50027',
}


def search_similar_styles(df_list, df_smv, cat1=None, cat2=None, cat3=None,
                          genders=None, keyword='', top_n=50,
                          sketch_features: dict | None = None,
                          df_proc: 'pd.DataFrame | None' = None):
    df = df_list.copy()
    if cat1:
        cat1_list = cat1 if isinstance(cat1, list) else [cat1]
        if cat1_list:
            mask = pd.Series(False, index=df.index)
            for c1 in cat1_list:
                mask |= df['CAT1'].str.contains(c1, na=False, case=False, regex=False)
            df = df[mask]
    if cat2:
        cat2_list = cat2 if isinstance(cat2, list) else [cat2]
        if cat2_list:
            mask = pd.Series(False, index=df.index)
            for c2 in cat2_list:
                kw = c2.split(')')[-1].strip() if ')' in c2 else c2
                mask |= df['CAT2'].str.contains(kw, na=False, case=False, regex=False)
            df = df[mask]
    if cat3:
        cat3_list = cat3 if isinstance(cat3, list) else [cat3]
        if cat3_list:
            mask = pd.Series(False, index=df.index)
            for c3 in cat3_list:
                kw = c3.split(')')[-1].strip() if ')' in c3 else c3
                mask |= df['CAT3'].str.contains(kw, na=False, case=False, regex=False)
            df = df[mask]
    if genders:
        genders_norm = [g.strip().title() for g in genders]
        df = df[df['GENDER'].astype(str).str.strip().str.title().isin(genders_norm)]
    if keyword:
        style_match = df['STYLE'].astype(str).str.contains(keyword, na=False, case=False, regex=False)
        if df_proc is not None:
            proc_styles = df_proc[
                df_proc['PROCESS'].astype(str).str.contains(keyword, na=False, case=False, regex=False) |
                df_proc['MACHINE'].astype(str).str.contains(keyword, na=False, case=False, regex=False)
            ]['STYLE'].astype(str).str.strip().unique()
            proc_match = df['STYLE'].astype(str).str.strip().isin(proc_styles)
            df = df[style_match | proc_match]
        else:
            df = df[style_match]

    smv_lookup = df_smv.drop_duplicates('STYLE')[['STYLE', 'TOTAL_SMV', 'PROC_COUNT', 'MACHINES']].copy()
    smv_lookup['STYLE'] = smv_lookup['STYLE'].astype(str).str.strip()
    df['STYLE'] = df['STYLE'].astype(str).str.strip()

    alias_rows = []
    for alias, canonical in STYLE_ALIAS.items():
        canon_row = smv_lookup[smv_lookup['STYLE'] == canonical]
        if not canon_row.empty:
            row = canon_row.copy()
            row['STYLE'] = alias
            alias_rows.append(row)
    if alias_rows:
        smv_lookup = pd.concat([smv_lookup] + alias_rows, ignore_index=True)

    df = df.merge(smv_lookup, on='STYLE', how='inner')

    return df.head(top_n).reset_index(drop=True)


def get_style_processes(df_proc, style_name, df_smv=None):
    style_str = str(style_name).strip()
    df = df_proc[df_proc['STYLE'].astype(str).str.strip() == style_str].copy()
    if not df.empty:
        return df.sort_values('NO').reset_index(drop=True)

    if df_smv is not None:
        row = df_smv[df_smv['STYLE'].astype(str).str.strip() == style_str]
        if not row.empty and 'CAT4' in row.columns:
            cat4 = str(row['CAT4'].values[0]).strip()
            style_name_from_cat4 = cat4.split('-', 1)[-1].strip() if '-' in cat4 else cat4
            df = df_proc[df_proc['STYLE'].astype(str).str.upper().str.contains(
                style_name_from_cat4[:15].upper(), na=False, regex=False)].copy()
            if not df.empty:
                return df.sort_values('NO').reset_index(drop=True)

    df = df_proc[df_proc['STYLE'].astype(str).str.upper().str.contains(
        style_str[:10].upper(), na=False, regex=False)].copy()
    return df.sort_values('NO').reset_index(drop=True)
