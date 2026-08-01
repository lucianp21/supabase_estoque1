import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import pandas as pd

# 1. Configuração da página do aplicativo
st.set_page_config(page_title="Estoque Padaria", page_icon="🥖", layout="wide")

# 2. Conectar ao Supabase
st_supabase = st.connection("supabase", type=SupabaseConnection)

st.title("🥖 Controle de Estoque & Movimentação Diária")

# Categorias Pré-carregadas
CATEGORIAS_PADRAO = ["Pão francês", "Assados", "Fritos", "Outra..."]

# Busca produtos cadastrados
resposta_produtos = st_supabase.table("produtos").select("*").execute()
produtos = resposta_produtos.data

# --- TABELA DE ESTOQUE ATUAL ---
st.header("📋 Saldo Atual do Estoque")
if produtos:
    dados_exibicao = [
        {
            "ID": p.get("id"),
            "Nome": p.get("nome"),
            "Quantidade Total": p.get("quantidade"),
            "Categoria": p.get("categoria", "Sem Categoria")
        }
        for p in produtos
    ]
    st.dataframe(dados_exibicao, use_container_width=True)
else:
    st.info("Nenhum produto cadastrado no catálogo.")

st.divider()

# --- NAVEGAÇÃO POR ABAS ---
aba_mov, aba_hist, aba_cad, aba_edit, aba_del = st.tabs([
    "⚡ Registrar Movimentação", 
    "📜 Histórico Diário", 
    "➕ Novo Produto", 
    "✏️ Editar", 
    "🗑️ Excluir"
])

# 1. REGISTRAR MOVIMENTAÇÃO (ENTRADA / SAÍDA RÁPIDA EM LOTE)
with aba_mov:
    st.subheader("Registrar Movimentação de Estoque")
    
    if produtos:
        st.write("Ajuste a quantidade movimentada dos produtos desejados e clique em **Salvar Todas as Movimentações**:")
        
        # Tipo de operação global
        tipo_mov = st.radio("Tipo de Movimentação do Lote", ["Entrada (Adicionar)", "Saída (Retirar)"], horizontal=True)
        is_entrada = "Entrada" in tipo_mov
        tipo_texto = "Entrada" if is_entrada else "Saída"

        # Prepara DataFrame para edição rápida na tela
        df_produtos = pd.DataFrame(produtos)
        df_produtos["Qtd Movimentar"] = 0  # Coluna zerada para preenchimento do usuário
        
        # Tabela editável
        df_editado = st.data_editor(
            df_produtos[["id", "nome", "quantidade", "Qtd Movimentar"]],
            column_config={
                "id": None,  # Oculta o ID na tela
                "nome": st.column_config.Column("Produto", disabled=True),
                "quantidade": st.column_config.NumberColumn("Estoque Atual", disabled=True),
                "Qtd Movimentar": st.column_config.NumberColumn("Qtd Movimentada", min_value=0, step=1)
            },
            hide_index=True,
            use_container_width=True,
            key="editor_movimentacao"
        )

        if st.button("💾 Salvar Todas as Movimentações", type="primary", use_container_width=True):
            # Filtra apenas itens com alteração de quantidade (> 0)
            movimentacoes_para_processar = df_editado[df_editado["Qtd Movimentar"] > 0]
            
            if movimentacoes_para_processar.empty:
                st.warning("Nenhuma quantidade foi informada (tudo permanece zerado).")
            else:
                erros = []
                sucessos = 0
                
                for _, row in movimentacoes_para_processar.iterrows():
                    # Garantindo conversão explícita para tipos nativos do Python (previne erro de JSON)
                    prod_id = row["id"]
                    nome_prod = str(row["nome"])
                    qtd_atual = int(row["quantidade"])
                    qtd_mov = int(row["Qtd Movimentar"])
                    
                    novo_saldo = qtd_atual + qtd_mov if is_entrada else qtd_atual - qtd_mov
                    
                    if not is_entrada and novo_saldo < 0:
                        erros.append(f"'{nome_prod}' não possui estoque suficiente para saída de {qtd_mov} un. (Atual: {qtd_atual})")
                    else:
                        # 1. Atualiza o saldo na tabela 'produtos'
                        st_supabase.table("produtos").update({"quantidade": int(novo_saldo)}).eq("id", prod_id).execute()
                        
                        # 2. Insere a movimentação no histórico (o banco grava a data/hora automaticamente)
                        st_supabase.table("movimentacoes").insert({
                            "produto_id": prod_id,
                            "nome_produto": nome_prod,
                            "tipo": tipo_texto,
                            "quantidade": int(qtd_mov)
                        }).execute()
                        sucessos += 1

                if erros:
                    for err in erros:
                        st.error(err)
                if sucessos > 0:
                    st.success(f"{sucessos} movimentação(ões) de {tipo_texto.lower()} registrada(s) com sucesso!")
                    st.rerun()
    else:
        st.info("Cadastre um produto antes de registrar movimentações.")

# 2. HISTÓRICO DIÁRIO
with aba_hist:
    st.subheader("Extrato de Movimentações Registradas")
    resposta_hist = st_supabase.table("movimentacoes").select("*").order("data_movimento", desc=True).execute()
    historico = resposta_hist.data
    
    if historico:
        dados_hist = [
            {
                "Data/Hora": p.get("data_movimento"),
                "Produto": p.get("nome_produto"),
                "Tipo": p.get("tipo"),
                "Quantidade": p.get("quantidade")
            }
            for p in historico
        ]
        st.dataframe(dados_hist, use_container_width=True)
    else:
        st.info("Nenhuma movimentação registrada no histórico ainda.")

# 3. CADASTRAR NOVO PRODUTO
with aba_cad:
    st.subheader("Cadastrar Novo Item no Catálogo")
    with st.form("form_novo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Produto (Ex: Pão Doce)")
            cat_selecionada = st.selectbox("Categoria", CATEGORIAS_PADRAO)
            cat_outra = st.text_input("Especifique a Categoria (se escolheu 'Outra...')")
        with col2:
            quantidade_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
        salvar_cad = st.form_submit_button("Cadastrar Produto")

    if salvar_cad:
        categoria_final = cat_outra.strip() if cat_selecionada == "Outra..." else cat_selecionada
        if not nome.strip():
            st.error("Por favor, digite o nome do produto!")
        else:
            st_supabase.table("produtos").insert({
                "nome": nome,
                "quantidade": int(quantidade_inicial),
                "categoria": categoria_final
            }).execute()
            st.success(f"'{nome}' cadastrado!")
            st.rerun()

# 4. EDITAR PRODUTO / CATEGORIA
with aba_edit:
    st.subheader("Editar Dados do Produto")
    if produtos:
        opcoes_edit = {p["id"]: p["nome"] for p in produtos}
        id_edit = st.selectbox("Selecione o produto para editar", options=list(opcoes_edit.keys()), format_func=lambda x: opcoes_edit[x], key="edit_sel")
        prod_edit = next((p for p in produtos if p["id"] == id_edit), None)
        
        if prod_edit:
            with st.form("form_edit"):
                novo_nome = st.text_input("Nome", value=prod_edit.get("nome", ""))
                
                cat_atual = prod_edit.get("categoria", "")
                idx_cat = CATEGORIAS_PADRAO.index(cat_atual) if cat_atual in CATEGORIAS_PADRAO else 3
                nova_cat_sel = st.selectbox("Categoria", CATEGORIAS_PADRAO, index=idx_cat)
                nova_cat_outra = st.text_input("Outra Categoria", value=cat_atual if idx_cat == 3 else "")
                
                nova_qtd = st.number_input("Ajustar Saldo Total Manualmente", min_value=0, step=1, value=int(prod_edit.get("quantidade", 0)))
                
                atualizar = st.form_submit_button("Salvar Alterações")
                if atualizar:
                    cat_final = nova_cat_outra.strip() if nova_cat_sel == "Outra..." else nova_cat_sel
                    st_supabase.table("produtos").update({
                        "nome": novo_nome,
                        "categoria": cat_final,
                        "quantidade": int(nova_qtd)
                    }).eq("id", id_edit).execute()
                    st.success("Produto atualizado!")
                    st.rerun()
    else:
        st.info("Nenhum produto cadastrado.")

# 5. EXCLUIR PRODUTO
with aba_del:
    st.subheader("Excluir Produto")
    if produtos:
        opcoes_del = {p["id"]: f"{p['nome']} | Saldo: {p['quantidade']}" for p in produtos}
        id_del = st.selectbox("Selecione para excluir", options=list(opcoes_del.keys()), format_func=lambda x: opcoes_del[x], key="del_sel")
        if st.button("🗑️ Confirmar Exclusão do Catálogo", type="primary"):
            st_supabase.table("produtos").delete().eq("id", id_del).execute()
            st.warning("Produto excluído!")
            st.rerun()
    else:
        st.info("Nenhum produto cadastrado.")

# --- NAVEGAÇÃO POR ABAS ---
aba_mov, aba_hist, aba_cad, aba_edit, aba_del = st.tabs([
    "⚡ Registrar Movimentação", 
    "📜 Histórico Diário", 
    "➕ Novo Produto", 
    "✏️ Editar", 
    "🗑️ Excluir"
])

# 1. REGISTRAR MOVIMENTAÇÃO (ENTRADA / SAÍDA)
with aba_mov:
    st.subheader("Registrar Entrada ou Saída de Estoque")
    if produtos:
        opcoes_mov = {p["id"]: f"{p['nome']} (Estoque atual: {p['quantidade']})" for p in produtos}
        prod_id_mov = st.selectbox("Selecione o Produto", options=list(opcoes_mov.keys()), format_func=lambda x: opcoes_mov[x])
        
        col1, col2 = st.columns(2)
        with col1:
            tipo_mov = st.radio("Tipo de Movimentação", ["Entrada (Adicionar)", "Saída (Retirar)"])
        with col2:
            qtd_mov = st.number_input("Quantidade", min_value=1, step=1, value=1)
            
        if st.button("Salvar Movimentação", type="primary"):
            prod_atual = next((p for p in produtos if p["id"] == prod_id_mov), None)
            if prod_atual:
                is_entrada = "Entrada" in tipo_mov
                tipo_texto = "Entrada" if is_entrada else "Saída"
                
                # Novo saldo calculado
                novo_saldo = prod_atual["quantidade"] + qtd_mov if is_entrada else prod_atual["quantidade"] - qtd_mov
                
                if not is_entrada and novo_saldo < 0:
                    st.error("Erro: A quantidade de saída é maior do que o estoque disponível!")
                else:
                    # 1. Atualiza o saldo na tabela 'produtos'
                    st_supabase.table("produtos").update({"quantidade": novo_saldo}).eq("id", prod_id_mov).execute()
                    
                    # 2. Insere a movimentação no histórico
                    st_supabase.table("movimentacoes").insert({
                        "produto_id": prod_id_mov,
                        "nome_produto": prod_atual["nome"],
                        "tipo": tipo_texto,
                        "quantidade": qtd_mov
                    }).execute()
                    
                    st.success(f"{tipo_texto} de {qtd_mov} unidade(s) de '{prod_atual['nome']}' registrada com sucesso!")
                    st.rerun()
    else:
        st.info("Cadastre um produto antes de registrar movimentações.")

# 2. HISTÓRICO DIÁRIO
with aba_hist:
    st.subheader("Extrato de Movimentações Registradas")
    resposta_hist = st_supabase.table("movimentacoes").select("*").order("data_movimento", desc=True).execute()
    historico = resposta_hist.data
    
    if historico:
        dados_hist = [
            {
                "Data/Hora": p.get("data_movimento"),
                "Produto": p.get("nome_produto"),
                "Tipo": p.get("tipo"),
                "Quantidade": p.get("quantidade")
            }
            for p in historico
        ]
        st.dataframe(dados_hist, use_container_width=True)
    else:
        st.info("Nenhuma movimentação registrada no histórico ainda.")

# 3. CADASTRAR NOVO PRODUTO
with aba_cad:
    st.subheader("Cadastrar Novo Item no Catálogo")
    with st.form("form_novo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Produto (Ex: Pão Doce)")
            cat_selecionada = st.selectbox("Categoria", CATEGORIAS_PADRAO)
            cat_outra = st.text_input("Especifique a Categoria (se escolheu 'Outra...')")
        with col2:
            quantidade_inicial = st.number_input("Estoque Inicial", min_value=0, step=1)
            
        salvar_cad = st.form_submit_button("Cadastrar Produto")

    if salvar_cad:
        categoria_final = cat_outra.strip() if cat_selecionada == "Outra..." else cat_selecionada
        if not nome.strip():
            st.error("Por favor, digite o nome do produto!")
        else:
            st_supabase.table("produtos").insert({
                "nome": nome,
                "quantidade": quantidade_inicial,
                "categoria": categoria_final
            }).execute()
            st.success(f"'{nome}' cadastrado!")
            st.rerun()

# 4. EDITAR PRODUTO / CATEGORIA
with aba_edit:
    st.subheader("Editar Dados do Produto")
    if produtos:
        opcoes_edit = {p["id"]: p["nome"] for p in produtos}
        id_edit = st.selectbox("Selecione o produto para editar", options=list(opcoes_edit.keys()), format_func=lambda x: opcoes_edit[x], key="edit_sel")
        prod_edit = next((p for p in produtos if p["id"] == id_edit), None)
        
        if prod_edit:
            with st.form("form_edit"):
                novo_nome = st.text_input("Nome", value=prod_edit.get("nome", ""))
                
                # Trata seleção de categoria pré-carregada
                cat_atual = prod_edit.get("categoria", "")
                idx_cat = CATEGORIAS_PADRAO.index(cat_atual) if cat_atual in CATEGORIAS_PADRAO else 3
                nova_cat_sel = st.selectbox("Categoria", CATEGORIAS_PADRAO, index=idx_cat)
                nova_cat_outra = st.text_input("Outra Categoria", value=cat_atual if idx_cat == 3 else "")
                
                nova_qtd = st.number_input("Ajustar Saldo Total Manualmente", min_value=0, step=1, value=int(prod_edit.get("quantidade", 0)))
                
                atualizar = st.form_submit_button("Salvar Alterações")
                if atualizar:
                    cat_final = nova_cat_outra.strip() if nova_cat_sel == "Outra..." else nova_cat_sel
                    st_supabase.table("produtos").update({
                        "nome": novo_nome,
                        "categoria": cat_final,
                        "quantidade": nova_qtd
                    }).eq("id", id_edit).execute()
                    st.success("Produto atualizado!")
                    st.rerun()
    else:
        st.info("Nenhum produto cadastrado.")

# 5. EXCLUIR PRODUTO
with aba_del:
    st.subheader("Excluir Produto")
    if produtos:
        opcoes_del = {p["id"]: f"{p['nome']} | Saldo: {p['quantidade']}" for p in produtos}
        id_del = st.selectbox("Selecione para excluir", options=list(opcoes_del.keys()), format_func=lambda x: opcoes_del[x], key="del_sel")
        if st.button("🗑️ Confirmar Exclusão do Catálogo", type="primary"):
            st_supabase.table("produtos").delete().eq("id", id_del).execute()
            st.warning("Produto excluído!")
            st.rerun()
    else:
        st.info("Nenhum produto cadastrado.")
