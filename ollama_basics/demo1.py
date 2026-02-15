from openpyxl import Workbook

def calc_counts(size):
    diff = size - 10
    max_c = diff // 2 + 1
    min_c = diff // 2 + (diff % 2)
    return max_c, min_c

wb = Workbook()
ws1 = wb.active
ws1.title = "1D_TestCases_Summary"
ws1.append(["TestCase_ID","Type","Size","Max_Count","Min_Count","Result"])

case_id = 1
for size in range(10, 101):
    max_c, min_c = calc_counts(size)
    result = (max_c + min_c) % size
    ws1.append([case_id, "1D", size, max_c, min_c, result])
    case_id += 1

ws2 = wb.create_sheet("2D_TestCases_Summary")
ws2.append(["TestCase_ID","Type","Size","Max_Count","Min_Count","Result"])
for m in range(10, 101):
    for n in range(10, 101):
        max_c, min_c = calc_counts(m)
        result = (max_c + min_c) % (m*n)
        ws2.append([case_id, "2D", f"{m}x{n}", max_c, min_c, result])
        case_id += 1

wb.save("Hackathon_TestCases.xlsx")
print("Excel file created successfully.")
