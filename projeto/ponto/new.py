import streamlit as st
from st_supabase_connection import SupabaseConnection

# 1. Configuração da página do aplicativo
st.set_page_config(page_title="Estoque Padaria", page_icon="🥖", layout="wide")

# 2. Conectar ao Supabase usando os dados salvos em .streamlit/secrets.toml
st_supabase = st.connection("supabase", type=SupabaseConnection)

st.title("🥖 Controle de Estoque - Padaria")

# --- VISUALIZAR ESTOQUE ---
st.header("📋 Estoque Atual")

# Faz uma busca no Supabase trazendo todos os itens da tabela 'produtos'
resposta = st_supabase.table("produtos").select("*").execute()
produtos = resposta.data

if produtos:
    # Exibe a lista de produtos em formato de tabela interativa
    st.dataframe(produtos, use_container_width=True)
else:
    st.info("Sua tabela ainda está vazia. Cadastre um produto abaixo!")

st.divider()

# --- ADICIONAR NOVO PRODUTO ---
st.header("➕ Cadastrar Produto")

with st.form("form_novo_produto", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input("Nome do Produto (Ex: Pão Francês)")
        categoria = st.selectbox("Categoria", ["Padaria", "Confeitaria", "Bebidas", "Outros"])
    
    with col2:
        quantidade = st.number_input("Quantidade Inicial em Estoque", min_value=0, step=1)
        preco = st.number_input("Preço (R$)", min_value=0.0, format="%.2f", step=0.50)
    
    botao_salvar = st.form_submit_button("Salvar no Banco de Dados")

# O que acontece ao clicar no botão de salvar
if botao_salvar:
    if nome.strip() == "":
        st.error("Por favor, digite o nome do produto!")
    else:
        # Envia os dados para a tabela 'produtos' no Supabase
        st_supabase.table("produtos").insert({
            "nome": nome,
            "quantidade": quantidade,
            "preco": preco,
            "categoria": categoria
        }).execute()
        
        st.success(f"Sucesso! '{nome}' foi salvo no Supabase.")
        st.rerun()  # Recarrega a tela para atualizar a lista