import streamlit as st


def main():
    if not st.user:
        print('no user')
    
    else:
        print('user found')


if __name__ == "__main__":
    main()
