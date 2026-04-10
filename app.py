import pandas as pd
import streamlit as st

st.title("EPAD Progress Tracker. Version 1.1")

uploaded_file = st.file_uploader("Upload EPAD CSV or Excel", type=["csv", "xlsx"])

if uploaded_file:
    # --- Select Part / Year ---
    st.subheader("Select Year")
    part = st.selectbox(
        "Choose EPAD Part",
        ["Part 1", "Part 2", "Part 3", "Part 4"]
    )

    # Load file
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

    def find_cols_prefix(prefix):
        return [c for c in df.columns if c.startswith(prefix)]

    def any_yes(row, columns):
        return "Yes" if any(is_completed(row[c]) for c in columns) else "No"

    def all_yes(row, columns):
        return "Yes" if all(is_yes(row[c]) for c in columns) else "No"

    def is_completed(value):
        if pd.isna(value):
            return False
        v = str(value).strip().lower()

        # ignore default / placeholder values
        if v in ["", "nan", "answer", "assessed by", "assessed on", "released", "not answered"]:
             return False
        return True

    # NEW: specifically check for "Yes"
    def is_yes(value):
        if pd.isna(value):
            return False

    def is_yes(value):
        if pd.isna(value):
            return False

        v = str(value).strip().lower()

        # ONLY explicit "yes" counts
        return v == "yes"



    def get_value(row, keyword):
        for col in df.columns:
            if keyword.lower() in col.lower():
                return row[col]
        return ""
    # --- Identify columns ---

    orientation_cols = find_cols_all([part, "Placement", "Orientation", "Declaration"]) + \
                       find_cols_all([part, "Placement", "Orientation", "Verification"])

    initial_cols = find_cols_all([part, "Placement", "Initial Interview", "Student"]) + \
                   find_cols_all([part, "Placement", "Initial Interview", "Practice Supervisor"]) + \
                   find_cols_all([part, "Placement", "Initial Interview", "Practice Assessor"])

    midpoint_cols = find_cols_all([part, "Placement", "Mid Point Interview", "Student"]) + \
                    find_cols_all([part, "Placement", "Mid Point Interview", "Practice Assessor"])

    final_cols = find_cols_all([part, "Placement", "Final Interview", "Student"]) + \
                 find_cols_all([part, "Placement", "Final Interview", "Practice Assessor"])

    progressing_final_cols = find_cols_all([
        part,
        "Placement",
        "Final Interview",
        "FAILING TO PROGRESS"
    ])

    progressing_mid_cols = find_cols_all([
        part,
        "Placement",
        "Mid Point Interview",
        "FAILING TO PROGRESS"
    ])

    prof_values_cols = [
        c for c in df.columns
        if part in c
        and "Professional Values in Practice" in c
        and "Final Assessment" in c
    ]




    # --- Process data ---
    output = []

    for _, row in df.iterrows():

        student = {}

        student["Student Name"] = f"{get_value(row, 'First name')} {get_value(row, 'Last name')}"

        student["Email"] = get_value(row, "Email")
        student["Cohort"] = get_value(row, "submission")

        student["Placement"] = get_value(row, "Placement Provider://Column 1")
        student["Placement Provider"] = get_value(row, "Placement Provider://Column 2")

        student["Orientation"] = any_yes(row, orientation_cols)
        student["Initial Interview"] = any_yes(row, initial_cols)
        student["Midpoint Interview"] = any_yes(row, midpoint_cols)
        student["Final Interview"] = any_yes(row, final_cols)

        student["Professional Values"] = all_yes(row, prof_values_cols)

        # Progressing logic
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
        # At Risk logic
        if (
            student["Progressing (Midpoint)"] == "No"
            or student["Progressing (Final)"] == "No"
            or student["Midpoint Interview"] == "No"
            or student["Final Interview"] == "No"
        ):
            student["At Risk"] = "Yes"
        else:
            student["At Risk"] = "No"

        output.append(student)



    result_df = pd.DataFrame(output)

    # --- Display ---

    # --- Filters ---
    st.subheader("Student Overview")
    st.subheader("Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        show_at_risk = st.checkbox("🔴 At Risk only")
    with col2:
        show_incomplete = st.checkbox("🟡 Incomplete only")
    with col3:
        show_on_track = st.checkbox("🟢 On Track only")

    search_name = st.text_input("🔍 Search student name")

    # --- Apply filters ---
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

    # --- Display filtered data ---
    # --- Colour coding ---
    def highlight_rows(row):
        if row["At Risk"] == "Yes":
            return ["background-color: #f8d7da"] * len(row)  # light red
        elif row["Final Interview"] == "No" or row["Midpoint Interview"] == "No":
            return ["background-color: #fff3cd"] * len(row)  # light amber
        else:
            return ["background-color: #d4edda"] * len(row)  # light green

    styled_df = filtered_df.style.apply(highlight_rows, axis=1)

    st.dataframe(styled_df, use_container_width=True)


    # --- Quick stats ---
    st.subheader("Summary")
    st.write(f"Total students: {len(result_df)}")

    st.write(f"Final interviews completed: {(result_df['Final Interview'] == 'Yes').sum()}")
    st.write(f"Professional values achieved: {(result_df['Professional Values'] == 'Yes').sum()}")
