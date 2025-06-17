import streamlit as st
import boto3
from io import BytesIO
from PIL import Image

PAGE_SIZE = 50

# --- Authentication ---

def authenticate():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if "auth_failed" not in st.session_state:
        st.session_state["auth_failed"] = False

    if st.button("Login"):
        if username in st.secrets["auth"] and st.secrets["auth"][username] == password:
            st.session_state["authenticated"] = True
            st.session_state["user"] = username
            st.session_state["auth_failed"] = False
        else:
            st.session_state["auth_failed"] = True

    if st.session_state["auth_failed"]:
        st.error("⚠️ Invalid username or password")

# --- AWS S3 client ---

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=st.secrets["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws_secret_access_key"]
    )

@st.cache_data
def list_top_level_folders(bucket):
    s3 = get_s3_client()
    response = s3.list_objects_v2(Bucket=bucket, Delimiter="/")
    prefixes = response.get("CommonPrefixes", [])
    return [p["Prefix"] for p in prefixes]

@st.cache_data
def list_images_in_folder(bucket, folder):
    s3 = get_s3_client()
    paginator = s3.get_paginator('list_objects_v2')
    image_keys = []

    for page in paginator.paginate(Bucket=bucket, Prefix=folder):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                image_keys.append(key)
    return image_keys

def get_image_from_s3(bucket, key):
    s3 = get_s3_client()
    response = s3.get_object(Bucket=bucket, Key=key)
    return Image.open(BytesIO(response['Body'].read()))

# --- Main app ---

def main():
    st.set_page_config(page_title="S3 Image Viewer", layout="wide")

    # Authentication gate
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        authenticate()
        return

    st.sidebar.write(f"👤 Logged in as: **{st.session_state['user']}**")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.experimental_rerun()

    st.title("🖼️ S3 Image Viewer with Pagination")

    bucket_name = st.secrets["aws_bucket_name"]

    if bucket_name:
        folders = list_top_level_folders(bucket_name)

        if not folders:
            st.warning("No folders found in the bucket.")
        else:
            #selected_folder = st.selectbox("Choose a top-level folder", folders)
            selected_folder = "sierra_poc2_insulators2_dino2_66b587ece7b433ff03455227_66b589a3c70d86c8306cdf86_75b29bb3/"

            if selected_folder:
                image_keys = list_images_in_folder(bucket_name, selected_folder)
                total_images = len(image_keys)
                total_pages = max(1, (total_images - 1) // PAGE_SIZE + 1)

                st.write(f"📸 Found {total_images} images in `{selected_folder}`")

                page_number = st.number_input(
                    f"Page (1 - {total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1
                )

                start_idx = (page_number - 1) * PAGE_SIZE
                end_idx = start_idx + PAGE_SIZE
                current_batch = image_keys[start_idx:end_idx]

                cols = st.columns(5)
                for idx, key in enumerate(current_batch):
                    with cols[idx % 5]:
                        try:
                            img = get_image_from_s3(bucket_name, key)
                            st.image(img, caption=key.split("/")[-1], use_container_width=True)
                        except Exception as e:
                            st.error(f"Error loading {key}: {e}")

if __name__ == "__main__":
    main()
