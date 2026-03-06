import json
import re

def main(args):
    # ==========================================
    # 1. 致命错误修正：Coze 的输入变量必须通过 args.params 获取！
    # ==========================================
    params = args.params
    raw_ai = params.get('identified_item', '')
    raw_price = params.get('price_list', '[]')

    # ==========================================
    # 2. 极简解析
    # ==========================================
    # 解析表格
    try:
        price_table = json.loads(raw_price) if isinstance(raw_price, str) else raw_price
    except Exception as e:
        return {"final_quote": 0, "message": f"表格解析失败: {str(e)}", "item_list": "Error"}

    # 解析 AI 输入 (处理 Markdown 标签)
    try:
        ai_clean = re.sub(r'```json|```', '', str(raw_ai)).strip()
        ai_items = json.loads(ai_clean)
        if isinstance(ai_items, dict):
            ai_items = [ai_items]
    except Exception as e:
        return {"final_quote": 0, "message": f"AI解析失败: {str(e)}", "item_list": "Error"}

    # ==========================================
    # 3. 计费与匹配逻辑
    # ==========================================
    def norm(s):
        # 移除非字母数字字符并转小写
        return re.sub(r'[^a-z0-9]', '', str(s).lower())

    total = 0.0
    names = []
    logs =[]

    for item in ai_items:
        t_name = str(item.get('service_item', ''))
        t_norm = norm(t_name)
        try:
            qty = float(item.get('quantity', 1))
        except:
            qty = 1.0
        hard = bool(item.get('is_difficult', False))

        matched = False
        for row in price_table:
            if not isinstance(row, list) or len(row) < 3:
                continue
            
            s_name = str(row[0])
            s_norm = norm(s_name)
            
            # 跳过表头
            if "serviceitem" in s_norm:
                continue

            # 核心匹配：包含逻辑 (Snow_Sidewalk 匹配 Snow: Sidewalk/Path)
            if t_norm and (t_norm in s_norm or s_norm in t_norm):
                try:
                    # 单价 (第3列)
                    base = float(re.sub(r'[^\d.]', '', str(row[2])))
                    
                    # 难度 (第4列)
                    factor = 1.0
                    if hard and len(row) > 3:
                        fm = re.search(r'(\d+\.\d+|\d+)', str(row[3]))
                        if fm: factor = float(fm.group(1))
                    
                    # 起步价 (第5列)
                    min_fee = 0.0
                    if len(row) > 4:
                        min_fee = float(re.sub(r'[^\d.]', '', str(row[4])))

                    # 计费规则: max(单价*数量*难度, 起步价)
                    subtotal = max(base * qty * factor, min_fee)
                    total += subtotal
                    
                    names.append(s_name)
                    logs.append(f"{s_name}: ${round(subtotal, 2)}")
                    matched = True
                    break
                except:
                    continue
        
        if not matched:
            names.append(f"{t_name}(?)")
            logs.append(f"{t_name}: 价格未匹配")

    # ==========================================
    # 4. 返回结果
    # ==========================================
    res = round(total, 2)
    return {
        "final_quote": res,
        "item_list": ", ".join(names),
        "message": f"Total: ${res} CAD. Details: {' | '.join(logs)}"
    }

    # 5. 生成带漂亮排版的最终报价单
    item_str = ", ".join(names_found) if names_found else "No items identified"
    
    final_text = (
        "Handy-Bot Service Quote 🛠️\n\n"
        f"Task Identified: {item_str}\n"
        f"Total Amount: ${round(total_amount, 2)} CAD\n\n"
        "Note: This estimate is based on the photo provided. Final price may vary upon arrival.\n\n"
        "Would you like to confirm this booking?"
    )
    
    return {
        "final_quote": round(total_amount, 2),
        "item_list": item_str,
        "message": final_text
    }