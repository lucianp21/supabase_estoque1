import streamlit as st
from st_supabase_connection import SupabaseConnection

# 1. Configuração da página do aplicativo
st.set_page_config(page_title="Estoque Padaria", page_icon="🥖", layout="wide")

# 2. Conectar ao Supabase usando os dados salvos nos Secrets
st_supabase = st.connection("supabase", type=SupabaseConnection)

st.title("🥖 Controle de Estoque - Padaria")

# --- VISUALIZAR ESTOQUE ---
st.header("📋 Estoque Atual")

# Busca todos os itens da tabela 'produtos'
resposta = st_supabase.table("produtos").select("*").execute()
produtos = resposta.data

if produtos:
    # Prepara os dados para exibição sem a coluna de preço
    dados_exibicao = []
    for p in produtos:
        dados_exibicao.append({
            "ID": p.get("id"),
            "Nome": p.get("nome"),
            "Quantidade": p.get("quantidade"),
            "Categoria": p.get("categoria", "Sem Categoria")
        })
    st.dataframe(dados_exibicao, use_container_width=True)
else:
    st.info("Sua tabela ainda está vazia. Cadastre um produto abaixo!")

st.divider()

# --- ABA DE AÇÕES (CADASTRAR, EDITAR, EXCLUIR) ---
aba_cadastrar, aba_editar, aba_excluir = st.tabs(["➕ Cadastrar Produto", "✏️ Editar Produto", "🗑️ Excluir Produto"])

# 1. ABA CADASTRAR
with aba_cadastrar:
    st.subheader("Novo Item no Estoque")
    with st.form("form_novo_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Produto (Ex: Pão Francês)")
            categoria = st.text_input("Categoria (Ex: Padaria, Confeitaria, Bebidas)")
        with col2:
            quantidade = st.number_input("Quantidade Inicial em Estoque", min_value=0, step=1)

        botao_salvar = st.form_submit_button("Salvar no Banco de Dados")

    if botao_salvar:
        if nome.strip() == "":
            st.error("Por favor, digite o nome do produto!")
        else:
            st_supabase.table("produtos").insert({
                "nome": nome,
                "quantidade": quantidade,
                "categoria": categoria
            }).execute()
            
            st.success(f"Sucesso! '{nome}' foi salvo no Supabase.")
            st.rerun()

# 2. ABA EDITAR CATEGORIA E DADOS
with aba_editar:
    st.subheader("Editar Produto ou Categoria")
    if produtos:
        opcoes_editar = {p["id"]: f"{p['nome']} (Categoria Atual: {p.get('categoria', 'Sem Categoria')})" for p in produtos}
        id_selecionado_editar = st.selectbox("Selecione o produto para editar", options=list(opcoes_editar.keys()), format_func=lambda x: opcoes_editar[x], key="select_editar")
        
        # Localiza o produto selecionado na lista
        prod_edit = next((p for p in produtos if p["id"] == id_selecionado_editar), None)
        
        if prod_edit:
            with st.form("form_editar_produto"):
                novo_nome = st.text_input("Nome do Produto", value=prod_edit.get("nome", ""))
                nova_categoria = st.text_input("Categoria", value=prod_edit.get("categoria", ""))
                nova_quantidade = st.number_input("Quantidade", min_value=0, step=1, value=int(prod_edit.get("quantidade", 0)))
                
                botao_atualizar = st.form_submit_button("Atualizar Produto")
                
                if botao_atualizar:
                    st_supabase.table("produtos").update({
                        "nome": novo_nome,
                        "categoria": nova_categoria,
                        "quantidade": nova_quantidade
                    }).eq("id", id_selecionado_editar).execute()
                    
                    st.success("Produto atualizado com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhum produto disponível para edição.")

# 3. ABA EXCLUIR REGISTRO
with aba_excluir:
    st.subheader("Remover Produto do Estoque")
    if produtos:
        opcoes_excluir = {p["id"]: f"{p['nome']} | Qtd: {p['quantidade']} | Categoria: {p.get('categoria', 'Sem Categoria')}" for p in produtos}
        id_selecionado_excluir = st.selectbox("Selecione o produto que deseja remover", options=list(opcoes_excluir.keys()), format_func=lambda x: opcoes_excluir[x], key="select_excluir")
        
        if st.button("🗑️ Confirmar Exclusão", type="primary"):
            st_supabase.table("produtos").delete().eq("id", id_selecionado_excluir).execute()
            st.warning("Registro excluído com sucesso!")
            st.rerun()
    else:
        st.info("Nenhum produto disponível para exclusão.")
