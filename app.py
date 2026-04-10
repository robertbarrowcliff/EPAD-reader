import pandas as pd
import streamlit as st

st.title("EPAD Progress Tracker. Version 2.0")

uploaded_file = st.file_uploader("Upload EPAD CSV or Excel", type=["csv", "xlsx"])

if uploaded_file:

    # --- Part → Placement mapping ---
    part_to_placements = {
        "Part 1": ["Placement 1", "Placement 2", "Retrieval Placement"],
        "Part 2": ["Placement 3", "Placement 4", "Retrieval Placement"],
        "Part 3": ["Placement 5", "Placement 6", "Retrieval Placement"],
        "Part 4": ["Placement 7", "Placement 8", "Retrieval Placement"],  # adjust if needed
    }

    # --- Selectors ---
    st.subheader("Select Placement")

    col1, col2 = st.columns(2)

    with col1:
        part = st.selectbox("Choose EPAD Part", list(part_to_placements.keys()))

    with col2:
        placement = st.selectbox("Choose Placement", part_to_placements[part])

    # --- Load file ---
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file, low_memory=False)
    else:
        df = pd.read_excel(uploaded_file)

    # --- Helper functions ---
    def find_cols_all(keywords):
        return [
            c for c in df.columns
            if all(k.lower() in c.lower() for k in keywords)
        ]

    def is_completed(value):
        if pd.isna(value):
            return False

        v = str(value).strip().lower()

        if v in ["", "nan", "answer", "assessed by", "assessed on", "released", "not answered"]:
            return False

        if any(k in v for k in ["yes", "complete", "completed", "achieved", "done", "pass"]):
            return True

        return False

    def any_yes(row, columns):
        return "Yes" if any(is_completed(row[c]) for c in columns) else "No"

    def get_value(row, keyword):
        for col in df.columns:
            if keyword.lower() in col.lower():
                return row[col]
        return ""

    # --- Identify columns (NOW placement-specific) ---
    orientation_cols = find_cols_all([part, placement, "Orientation"])
    initial_cols = find_cols_all([part, placement, "Initial Interview"])
    midpoint_cols = find_cols_all([part, placement, "Mid Point Interview"])
    final_cols = find_cols_all([part, placement, "Final Interview"])

    progressing_mid_cols = find_cols_all([part, placement, "Mid Point Interview", "FAILING TO PROGRESS"])
    progressing_final_cols = find_cols_all([part, placement, "Final Interview", "FAILING TO PROGRESS"])

    # --- Professional Values (CORRECTED) ---
    prof_values_cols = [
        c for c in df.columns
        if (
            part.lower() in c.lower()
            and placement.lower() in c.lower()
            and "professional values" in c.lower()
            and "final assessment" in c.lower()
            and any(f"/ {i}." in c for i in range(1, 16))
        )
    ]

    # DEBUG (remove later)
    st.write("DEBUG - PV columns found:", len(prof_values_cols))

    # --- Process data ---
    output = []

    for _, row in df.iterrows():

        student = {}

        student["Student Name"] = f"{get_value(row, 'First name')} {get_value(row, 'Last name')}"
        student["Email"] = get_value(row, "Email")
        student["Cohort"] = get_value(row, "submission")

        student["Placement"] = placement

        student["Orientation"] = any_yes(row, orientation_cols)
        student["Initial Interview"] = any_yes(row, initial_cols)
        student["Midpoint Interview"] = any_yes(row, midpoint_cols)
        student["Final Interview"] = any_yes(row, final_cols)

        # --- Professional Values ---
        completed_pv = sum(is_completed(row[c]) for c in prof_values_cols)
        total_pv = len(prof_values_cols)

        student["Professional Values"] = "Yes" if completed_pv == total_pv and total_pv > 0 else "No"
        student["PV Progress"] = f"{completed_pv}/{total_pv}" if total_pv > 0 else "0/0"

        # --- Progressing ---
        def get_progressing_status(row, columns):
            for col in columns:
                val = str(row[col]).strip().lower()
                if "not progressing" in val:
                    return "No"
                if "progressing" in val:
                    return "Yes"
            return "No"

        student["Progressing (Midpoint)"] = get_progressing_status(row, progressing_mid_cols)
        student["Progressing (Final)"] = get_progressing_status(row, progressing_final_cols)

        # --- At Risk ---
        if (
            student["Progressing (Midpoint)"] == "No"
            or student["Progressing (Final)"] == "No"
            or student["Midpoint Interview"] == "No"
            or student["Final Interview"] == "No"
        ):
            student["At Risk"] = "Yes"
        else:
            student["At Risk"] = "No"

        # --- Missing items ---
        missing = []

        if student["Orientation"] == "No":
            missing.append("Orientation")
        if student["Initial Interview"] == "No":
            missing.append("Initial Interview")
        if student["Midpoint Interview"] == "No":
            missing.append("Midpoint Interview")
        if student["Final Interview"] == "No":
            missing.append("Final Interview")
        if student["Professional Values"] == "No":
            missing.append("Professional Values")

        student["Missing Items"] = ", ".join(missing)

        output.append(student)

    result_df = pd.DataFrame(output)

    # --- Filters ---
    st.subheader("Student Overview")

    col1, col2, col3 = st.columns(3)

    with col1:
        show_at_risk = st.checkbox("🔴 At Risk only")
    with col2:
        show_incomplete = st.checkbox("🟡 Incomplete only")
    with col3:
        show_on_track = st.checkbox("🟢 On Track only")

    search_name = st.text_input("🔍 Search student name")

    filtered_df = result_df.copy()

    if show_at_risk:
        filtered_df = filtered_df[filtered_df["At Risk"] == "Yes"]

    if show_incomplete:
        filtered_df = filtered_df[
            (filtered_df["Midpoint Interview"] == "No") |
            (filtered_df["Final Interview"] == "No")
        ]

    if show_on_track:
        filtered_df = filtered_df[
            (filtered_df["At Risk"] == "No") &
            (filtered_df["Final Interview"] == "Yes")
        ]

    if search_name:
        filtered_df = filtered_df[
            filtered_df["Student Name"].str.contains(search_name, case=False, na=False)
        ]

    # --- Colour coding ---
    def highlight_rows(row):
        if row["At Risk"] == "Yes":
            return ["background-color: #f8d7da"] * len(row)
        elif row["Final Interview"] == "No" or row["Midpoint Interview"] == "No":
            return ["background-color: #fff3cd"] * len(row)
        else:
            return ["background-color: #d4edda"] * len(row)

    styled_df = filtered_df.style.apply(highlight_rows, axis=1)

    st.dataframe(styled_df, use_container_width=True)

    # --- Summary ---
    st.subheader("Summary")
    st.write(f"Total students: {len(result_df)}")
    st.write(f"Final interviews completed: {(result_df['Final Interview'] == 'Yes').sum()}")
    st.write(f"Professional values achieved: {(result_df['Professional Values'] == 'Yes').sum()}")
