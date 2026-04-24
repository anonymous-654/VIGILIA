import streamlit as st
from enums import AttackType, EvalType
from profiles import PROFILES
from session import run_class_session
from vigilance.session import run_class_session_for_vigilance


profiles = PROFILES
subject = "Computer Science"
topic = "Introduction to Computer Science"

st.set_page_config(page_title="Classroom Simulator", page_icon="🎓", layout="wide")
st.title("🎓 Classroom Simulator")

with st.sidebar:
    st.header("Settings")
    model_path = st.text_input("Model path", value="gpt-4.1-mini")

    profile_type = st.selectbox(
        "Profile type",
        options=list(profiles.keys()),
        index=0
    )

    eval_type = st.selectbox(
        "Eval type",
        options=list(EvalType),
        index=0,
        format_func=lambda e: e.value
    )

    attack_type = st.selectbox(
        "Attack type",
        options=list(AttackType),
        index=0, \
        format_func=lambda e: e.value
    )

    run_btn = st.button("▶️ Run full class session", use_container_width=True)

# keep results so it doesn't re-run every rerender
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn:
    students = profiles[profile_type]
    with st.spinner("Running full conversation..."):
        if eval_type == "vigilance":
                (conversation_history, selected_speakers, selected_speaker_indices, 
                all_hand_raises, num_questions, 
                questions_asked, wrong_answers, num_wrong_answers,  vigilance_list, turns_ran, tpt, tct) = run_class_session_for_vigilance(students, model_path, subject, topic, profile_type, attack_type)

                st.session_state.result = {
                    "mode": "vigilance",
                    "attack_type": attack_type,
                    "conversation_history": conversation_history,
                    "selected_speakers": selected_speakers,
                    "selected_speaker_indices": selected_speaker_indices,
                    "all_hand_raises": all_hand_raises,
                    "num_questions": num_questions,
                    "questions_asked": questions_asked,
                    "wrong_answers": wrong_answers,
                    "num_wrong_answers": num_wrong_answers,
                    "vigilance_list": vigilance_list,
                    "turns_ran": turns_ran,
                    "tpt": tpt,
                    "tct": tct,
                    "profile_type": profile_type,
                }

        else:
            (
                conversation_history,
                selected_speakers,
                selected_speaker_indices,
                all_hand_raises,
                num_questions,
                turns_ran,
                tpt,
                tct,
            ) = run_class_session(
                students=students,
                model_path=model_path,
                profile_type=profile_type,
            )

            st.session_state.result = {
                "conversation_history": conversation_history,
                "selected_speakers": selected_speakers,
                "selected_speaker_indices": selected_speaker_indices,
                "all_hand_raises": all_hand_raises,
                "num_questions": num_questions,
                "turns_ran": turns_ran,
                "tpt": tpt,
                "tct": tct,
                "profile_type": profile_type,
            }

# ----- DISPLAY -----
if st.session_state.result is None:
    st.info("Pick a profile and click **Run full class session**.")
else:
    # res = st.session_state.result

    # c1, c2, c3, c4 = st.columns(4)
    # c1.metric("Turns ran", res["turns_ran"])
    # c2.metric("Student questions", res["num_questions"])
    # c3.metric("Prompt tokens", res["tpt"])
    # c4.metric("Completion tokens", res["tct"])

    # st.subheader("Transcript")
    # lines = []
    # for item in res["conversation_history"]:
    #     speaker = item.get("speaker", "")
    #     action = item.get("action", "")
    #     seg = item.get("segment", "")
    #     utt = item.get("utterance", "")
    #     # lines.append(f"{speaker} [{action}] (segment {seg})\n{utt}")
    #     lines.append(f"{speaker}: {utt}")

    # st.text_area("Conversation", value="\n\n".join(lines), height=550)

    res = st.session_state.result

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Turns ran", res["turns_ran"])
    c2.metric("Student questions", res["num_questions"])
    c3.metric("Prompt tokens", res["tpt"])
    c4.metric("Completion tokens", res["tct"])

    st.subheader("Transcript")

    wrong_texts = set(res.get("wrong_answers", []))

    html = (
        "<div style='height:550px; overflow-y:auto; border:1px solid #ddd; "
        "padding:10px; border-radius:6px; background:#fff;'>"
    )

    for item in res["conversation_history"]:
        speaker = item.get("speaker", "")
        action = item.get("action", "")
        utt = item.get("utterance", "")

        is_wrong = (action == "Answer" and utt in wrong_texts)

        # color wrong student answers red; optionally teacher blue
        color = "red" if is_wrong else ("#1f77b4" if speaker == "Teacher" else "black")
        weight = 700 if (is_wrong or speaker == "Teacher") else 400

        html += (
            "<div style='margin-bottom:12px;'>"
            f"<span style='color:{color}; font-weight:{weight};'>{speaker}:</span> "
            f"<span>{utt}</span>"
            "</div>"
        )

    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)

    with st.expander("Fairness / debug logs"):
        st.write("Profile type:", res["profile_type"])
        st.write("Selected speakers:", res["selected_speakers"])
        st.write("Selected speaker indices:", res["selected_speaker_indices"])
        st.write("All hand raises:", res["all_hand_raises"])

    with st.expander("Epistemic Vigilance logs"):
        st.write("Total number of questions:", res["num_questions"])
        st.write("Question asked:", res["questions_asked"])
        st.write("Total wrong answers:", res["num_wrong_answers"])
        st.write("Wrong answers:", res["wrong_answers"])
        st.write("Vigilance list:", res["vigilance_list"])