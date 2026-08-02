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
aba_mov, aba_hist, aba_del_mov, aba_cad, aba_edit, aba_del_prod = st.tabs([
    "⚡ Registrar Movimentação", 
    "📜 Histórico Diário", 
    "↩️ Excluir Movimentação",
    "➕ Novo Produto", 
    "✏️ Editar Produto", 
    "🗑️ Excluir Produto"
])

# 1. REGISTRAR MOVIMENTAÇÃO (ENTRADA / SAÍDA RÁPIDA EM LOTE)
with aba_mov:
    st.subheader("Registrar Movimentação de Estoque")
    
    if produtos:
        st.write("Ajuste a quantidade movimentada dos produtos desejados e clique em **Salvar Todas as Movimentações**:")
        
        tipo_mov = st.radio("Tipo de Movimentação do Lote", ["Entrada (Adicionar)", "Saída (Retirar)"], horizontal=True, key="radio_tipo_mov")
        is_entrada = "Entrada" in tipo_mov
        tipo_texto = "Entrada" if is_entrada else "Saída"

        df_produtos = pd.DataFrame(produtos)
        # Garante a coluna categoria tratada
        if "categoria" not in df_produtos.columns:
            df_produtos["categoria"] = "Sem Categoria"
        else:
            df_produtos["categoria"] = df_produtos["categoria"].fillna("Sem Categoria")
            
        df_produtos["Qtd Movimentar"] = 0
        
        # Tabela editável incluindo Categoria
        df_editado = st.data_editor(
            df_produtos[["id", "nome", "categoria", "quantidade", "Qtd Movimentar"]],
            column_config={
                "id": None,  # Oculta o ID
                "nome": st.column_config.Column("Produto", disabled=True),
                "categoria": st.column_config.Column("Categoria", disabled=True),
                "quantidade": st.column_config.NumberColumn("Estoque Atual", disabled=True),
                "Qtd Movimentar": st.column_config.NumberColumn("Qtd Movimentada", min_value=0, step=1)
            },
            hide_index=True,
            use_container_width=True,
            key="editor_movimentacao_lote"
        )

        if st.button("💾 Salvar Todas as Movimentações", type="primary", use_container_width=True, key="btn_salvar_lote"):
            movimentacoes_para_processar = df_editado[df_editado["Qtd Movimentar"] > 0]
            
            if movimentacoes_para_processar.empty:
                st.warning("Nenhuma quantidade foi informada (tudo permanece zerado).")
            else:
                erros = []
                sucessos = 0
                
                for _, row in movimentacoes_para_processar.iterrows():
                    prod_id = row["id"]
                    nome_prod = str(row["nome"])
                    qtd_atual = int(row["quantidade"])
                    qtd_mov = int(row["Qtd Movimentar"])
                    
                    novo_saldo = qtd_atual + qtd_mov if is_entrada else qtd_atual - qtd_mov
                    
                    if not is_entrada and novo_saldo < 0:
                        erros.append(f"'{nome_prod}' não possui estoque suficiente para saída de {qtd_mov} un. (Atual: {qtd_atual})")
                    else:
                        st_supabase.table("produtos").update({"quantidade": int(novo_saldo)}).eq("id", prod_id).execute()
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
                "ID Movimentação": p.get("id"),
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

# 3. EXCLUIR MOVIMENTAÇÃO EM LOTE (SELEÇÃO MÚLTIPLA)
with aba_del_mov:
    st.subheader("Excluir Múltiplas Movimentações")
    
    resposta_hist_del = st_supabase.table("movimentacoes").select("*").order("data_movimento", desc=True).execute()
    historico_del = resposta_hist_del.data
    
    if historico_del:
        st.write("Marque as movimentações que deseja apagar. **O estoque dos produtos será estornado automaticamente.**")
        
        df_hist = pd.DataFrame(historico_del)
        
        tabela_selecao = st.data_editor(
            df_hist[["id", "data_movimento", "nome_produto", "tipo", "quantidade"]],
            column_config={
                "id": st.column_config.Column("ID", disabled=True),
                "data_movimento": st.column_config.Column("Data/Hora", disabled=True),
                "nome_produto": st.column_config.Column("Produto", disabled=True),
                "tipo": st.column_config.Column("Tipo", disabled=True),
                "quantidade": st.column_config.NumberColumn("Quantidade", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key="editor_selecao_múltipla_mov"
        )
        
        movs_selecionadas = st.multiselect(
            "Selecione os IDs das movimentações para excluir:",
            options=[m["id"] for m in historico_del],
            format_func=lambda x: next((f"ID {m['id']} - {m['nome_produto']} ({m['tipo']}: {m['quantidade']}un)" for m in historico_del if m["id"] == x), str(x)),
            key="multiselect_movimentacoes_del"
        )
        
        if movs_selecionadas:
            st.warning(f"⚠️ Você selecionou **{len(movs_selecionadas)}** movimentação(ões) para excluir.")
            
            if st.button("🗑️ Confirmar Exclusão Selecionada", type="primary", use_container_width=True, key="btn_confirmar_del_mov_lote"):
                erros = []
                sucessos = 0
                
                for id_mov in movs_selecionadas:
                    mov = next((m for m in historico_del if m["id"] == id_mov), None)
                    if mov:
                        prod_id = mov.get("produto_id")
                        qtd_mov = int(mov.get("quantidade", 0))
                        tipo_mov = mov.get("tipo")
                        
                        resp_prod_atual = st_supabase.table("produtos").select("quantidade").eq("id", prod_id).execute()
                        
                        if resp_prod_atual.data:
                            qtd_estoque_atual = int(resp_prod_atual.data[0]["quantidade"])
                            novo_estoque = qtd_estoque_atual - qtd_mov if "Entrada" in tipo_mov else qtd_estoque_atual + qtd_mov
                            
                            if novo_estoque < 0:
                                erros.append(f"A movimentação ID {id_mov} ({mov['nome_produto']}) deixaria o estoque negativo.")
                            else:
                                st_supabase.table("produtos").update({"quantidade": int(novo_estoque)}).eq("id", prod_id).execute()
                                st_supabase.table("movimentacoes").delete().eq("id", id_mov).execute()
                                sucessos += 1
                        else:
                            st_supabase.table("movimentacoes").delete().eq("id", id_mov).execute()
                            sucessos += 1

                if erros:
                    for err in erros:
                        st.error(err)
                if sucessos > 0:
                    st.success(f"{sucessos} movimentação(ões) excluída(s) e estoque(s) ajustado(s) com sucesso!")
                    st.rerun()
    else:
        st.info("Nenhuma movimentação registrada no histórico para excluir.")

# 4. CADASTRAR NOVO PRODUTO
with aba_cad:
    st.subheader("Cadastrar Novo Item no Catálogo")
    with st.form("form_novo_produto", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Produto (Ex: Pão Doce)")
            cat_selecionada = st.selectbox("Categoria", CATEGORIAS_PADRAO, key="cat_cad_sel")
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

# 5. EDITAR PRODUTO / CATEGORIA
with aba_edit:
    st.subheader("Editar Dados do Produto")
    if produtos:
        opcoes_edit = {p["id"]: p["nome"] for p in produtos}
        id_edit = st.selectbox(
            "Selecione o produto para editar", 
            options=list(opcoes_edit.keys()), 
            format_func=lambda x: opcoes_edit[x], 
            key="selectbox_editar_produto"
        )
        prod_edit = next((p for p in produtos if p["id"] == id_edit), None)
        
        if prod_edit:
            with st.form("form_editar_produto"):
                novo_nome = st.text_input("Nome", value=prod_edit.get("nome", ""))
                
                cat_atual = prod_edit.get("categoria", "")
                idx_cat = CATEGORIAS_PADRAO.index(cat_atual) if cat_atual in CATEGORIAS_PADRAO else 3
                nova_cat_sel = st.selectbox("Categoria", CATEGORIAS_PADRAO, index=idx_cat, key="cat_edit_sel")
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

# 6. EXCLUIR PRODUTO DO CATÁLOGO
with aba_del_prod:
    st.subheader("Excluir Produto do Catálogo")
    if produtos:
        opcoes_del = {p["id"]: f"{p['nome']} | Saldo: {p['quantidade']}" for p in produtos}
        id_del = st.selectbox(
            "Selecione para excluir", 
            options=list(opcoes_del.keys()), 
            format_func=lambda x: opcoes_del[x], 
            key="selectbox_excluir_produto"
        )
        if st.button("🗑️ Confirmar Exclusão do Catálogo", type="primary", key="btn_excluir_prod"):
            st_supabase.table("produtos").delete().eq("id", id_del).execute()
            st.warning("Produto excluído!")
            st.rerun()
    else:
        st.info("Nenhum produto cadastrado.")
