import { useEffect, useState } from "react";
import api from "../../services/api";
import CustomDropdown from "../common/CustomDropdown";
import { useSelectedStatus } from "../../hooks/useSelectedStatus";

// Component สำหรับแสดงแถวของกระจกในตาราง
function GlassTableRow({ item, isActive, onClick, stockData = {} }) {
  const sku = item.sku;
  const variantCode = item.variantCode || null;
  const sqft = 0; // กระจกใน list ยังไม่มีขนาดเฉพาะ
  const isSelected = useSelectedStatus(sku, variantCode, sqft);

  return (
    <tr
      className={`grid grid-cols-12 gap-2 items-center cursor-pointer
        hover:bg-blue-50 transition
        ${isActive ? "bg-blue-100" : ""}
      `}
      onClick={onClick}
    >
      <td className="col-span-2 p-2 truncate">
        <div className="text-xs">{item.sku}</div>
        {item.sku2 && <div className="text-xs text-gray-500">{item.sku2}</div>}
      </td>
      <td className={`col-span-4 p-2 truncate ${isSelected ? 'text-blue-600 font-semibold' : ''}`}>
        {isSelected && <span className="mr-1">✓</span>}
        {item.description}
      </td>
      <td className="col-span-2 p-2 truncate">{item.subGroupName}</td>
      <td className="col-span-2 p-2 text-center whitespace-nowrap">
        {item.width} × {item.height}
      </td>
      <td className="col-span-1 p-2 text-center">{item.thickness}</td>
      <td className="col-span-1 p-2 text-center font-semibold">{item.inventory || stockData[item.sku] || 0}</td>
    </tr>
  );
}

export default function GlassPickerModal({ open, onClose, onConfirm }) {
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [glassList, setGlassList] = useState([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [total, setTotal] = useState(0);

  // FILTERS
  const [search, setSearch] = useState("");
  const [variantOnly, setVariantOnly] = useState(false);
  const [brandFilter, setBrandFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [subGroupFilter, setSubGroupFilter] = useState("");
  const [colorFilter, setColorFilter] = useState("");
  const [thickFilter, setThickFilter] = useState("");

  // SELECTION
  const [selectedItem, setSelectedItem] = useState(null);

  // SIZE INPUTS
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [unitW, setUnitW] = useState("inch");
  const [unitH, setUnitH] = useState("inch");

  // RESULT
  const [calcResult, setCalcResult] = useState(null);

  // NEW VARIABLES
  const [qtyCustomer, setQtyCustomer] = useState(1);
  const [qtySku, setQtySku] = useState(1);
  const [priceMode, setPriceMode] = useState("actual");
  const [isSoldByPack, setIsSoldByPack] = useState(false); // ⭐ checkbox ขายยกแพ็ก

  // ⭐ MULTI-SELECT STATE
  const [selectedItems, setSelectedItems] = useState([]);

  // STOCK DATA
  const [stockData, setStockData] = useState({});

  // FILTER OPTIONS
  const [filterOptions, setFilterOptions] = useState({
    brands: [],
    types: [],
    subGroups: [],
    colors: [],
    thicknesses: [],
  });

  // STEP SIZE
  const STEPS = [12, 18, 24, 30, 36, 42, 48, 60, 72, 84, 96, 120, 144];

  const isVariant = !!selectedItem?.isVariant;

  // -------------------------
  // FUNCTIONS
  // -------------------------
  function convertToInch(val, unit) {
    if (!val) return 0;
    val = Number(val);
    switch (unit) {
      case "cm":
        return val / 2.54;
      case "mm":
        return val / 25.4;
      case "ft":
        return val * 12;
      default:
        return val;
    }
  }

  function roundSize(inchVal) {
    if (inchVal > 144) return inchVal;
    for (let s of STEPS) {
      if (inchVal <= s) return s;
    }
    return inchVal;
  }

  // -------------------------
  // LOAD GLASS LIST (with pagination)
  // -------------------------
  const loadGlass = async (reset = false, searchQuery = "") => {
    if (!hasMore && !reset) return;

    // แยก loading state
    if (reset) {
      setLoading(true);
    } else {
      if (loadingMore) return;
      setLoadingMore(true);
    }

    const currentOffset = reset ? 0 : offset;

    try {
      const params = {
        limit: 10,
        offset: currentOffset,
      };

      // เพิ่ม filters
      if (brandFilter) params.brand = brandFilter;
      if (typeFilter) params.type = typeFilter;
      if (subGroupFilter) params.subGroup = subGroupFilter;
      if (colorFilter) params.color = colorFilter;
      if (thickFilter) params.thickness = thickFilter;
      if (searchQuery && searchQuery.trim()) params.search = searchQuery.trim();
      if (variantOnly) params.isVariant = true;

      console.log('🔍 Glass search params:', params);

      const res = await api.get("/api/items/glass/list", { params });
      
      const newItems = res.data.items || [];
      const totalCount = res.data.total || 0;

      console.log(`✅ Glass search results: ${newItems.length}/${totalCount} items`);

      setGlassList((prev) => (reset ? newItems : [...prev, ...newItems]));
      setTotal(totalCount);

      const newOffset = currentOffset + newItems.length;
      setOffset(newOffset);
      setHasMore(newOffset < totalCount);

      // ⭐ ดึง stock สำหรับ items ใหม่
      if (reset) {
        const newStockData = {};
        for (const item of newItems) {
          try {
            const stockRes = await api.get(`/api/items/glass/${item.sku}/stock`);
            newStockData[item.sku] = stockRes.data.quantity || 0;
          } catch (err) {
            console.error(`Error fetching stock for ${item.sku}:`, err);
            newStockData[item.sku] = 0;
          }
        }
        setStockData(newStockData);
      }

      if (reset) {
        const loadTime = performance.now();
        console.log(`✅ Glass list loaded (${newItems.length}/${totalCount} items)`);
      }
    } catch (err) {
      console.error("Error loading glass:", err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // -------------------------
  // EFFECT 1: LOAD INITIAL
  // -------------------------
  useEffect(() => {
    if (!open) return;

    setGlassList([]);
    setOffset(0);
    setHasMore(true);
    setTotal(0);
    setSelectedItem(null);
    setSearch("");

    loadGlass(true);
  }, [open]);

  // -------------------------
  // EFFECT 2: RELOAD ON FILTER CHANGE
  // -------------------------
  useEffect(() => {
    if (!open) return;

    setGlassList([]);
    setOffset(0);
    setHasMore(true);
    loadGlass(true, search);
  }, [brandFilter, typeFilter, subGroupFilter, colorFilter, thickFilter, variantOnly]);

  // -------------------------
  // EFFECT 3: RELOAD ON SEARCH (debounced)
  // -------------------------
  useEffect(() => {
    if (!open) return;

    const timer = setTimeout(() => {
      setGlassList([]);
      setOffset(0);
      setHasMore(true);
      loadGlass(true, search);
    }, 300);

    return () => clearTimeout(timer);
  }, [search]);

  // -------------------------
  // EFFECT: RESET calcResult WHEN sku changes
  // -------------------------
  useEffect(() => {
    setCalcResult(null);
  }, [selectedItem]);

  useEffect(() => {
    setWidth("");
    setHeight("");
  }, [selectedItem]);

  // -------------------------
  // EFFECT: AUTO-CALCULATE
  // -------------------------
  useEffect(() => {
    if (!selectedItem) return;

    if (isVariant) {
      if (!width || !height) return;
    }

    handleCalculate();
  }, [selectedItem, width, height, qtyCustomer, unitW, unitH, isVariant]);

  useEffect(() => {
    if (open) {
      setSelectedItem(null);
      setWidth("");
      setHeight("");
      setQtyCustomer(1);
      setQtySku(1);
      setCalcResult(null);
      setPriceMode("actual");
      setSelectedItems([]); // ⭐ รีเซ็ตรายการที่เลือก
      setUnitW("inch");
      setUnitH("inch");
      setIsSoldByPack(false); // ⭐ รีเซ็ต checkbox
    }
  }, [open]);

  // -------------------------
  // LOAD FILTER OPTIONS (Dynamic - only show available options)
  // -------------------------
  useEffect(() => {
    if (!open) return;

    const loadFilterOptions = async () => {
      try {
        // ⭐ สร้าง params จาก filter ปัจจุบัน
        const params = {};
        if (brandFilter) params.brand = brandFilter;
        if (typeFilter) params.type = typeFilter;
        if (subGroupFilter) params.subGroup = subGroupFilter;
        if (colorFilter) params.color = colorFilter;
        if (thickFilter) params.thickness = thickFilter;

        const res = await api.get("/api/items/glass/filter-options", { params });
        setFilterOptions(res.data);
      } catch (err) {
        console.error("Error loading filter options:", err);
      }
    };

    loadFilterOptions();
  }, [open, brandFilter, typeFilter, subGroupFilter, colorFilter, thickFilter]);

  async function handleCalculate() {
    if (!selectedItem) return;

    let wRawInch, hRawInch;
    let wRound, hRound;

    // -------------------------
    // 1️⃣ แยก Variant / Non-Variant
    // -------------------------
    if (isVariant) {
      // 🔹 Variant: ใช้ขนาดที่กรอก
      wRawInch = convertToInch(width, unitW);
      hRawInch = convertToInch(height, unitH);

      wRound = roundSize(wRawInch);
      hRound = roundSize(hRawInch);
    } else {
      // 🔹 Non-Variant: ใช้ขนาดจาก SKU
      wRawInch = Number(selectedItem.width);
      hRawInch = Number(selectedItem.height);

      // ขนาด SKU ถือว่าเป็นขนาดปัดแล้ว
      wRound = wRawInch;
      hRound = hRawInch;
    }

    // -------------------------
    // 2️⃣ คำนวณพื้นที่
    // -------------------------
    const sqftRaw = (wRawInch * hRawInch) / 144;
    const sqftRounded = (wRound * hRound) / 144;

    const actualSqft = sqftRounded * qtyCustomer; // ✅ คิดแบบปัดตามที่คุณต้องการ

    // -------------------------
    // 3️⃣ payload ส่งไป backend (ใช้รูปแบบเดียวกัน)
    // -------------------------
    const payload = {
      sku: selectedItem.sku,
      widthRaw: wRawInch,
      heightRaw: hRawInch,
      widthRounded: wRound,
      heightRounded: hRound,
      sqftRaw,
      sqftRounded,
      qty: 1,
    };

    try {
      const res = await api.post("/api/items/glass/calc", payload);

      setCalcResult({
        ...res.data,
        actualSqft,
      });
    } catch (err) {
      console.error("CALC ERROR:", err);
    }
  }

  // -------------------------
  // ADD TO LIST (แทนการปิด modal ทันที)
  // -------------------------
  function handleAddToList() {
    if (!calcResult || !selectedItem) return;

    const sqftPerPiece = Number(calcResult.sqft || 0);

    // 1) คำนวณพื้นที่ตาม SKU × จำนวนแผ่น
    const skuSqft = ((selectedItem.width * selectedItem.height) / 144) * qtySku;

    // 2) เลือก sqft ที่ต้องใช้คิดราคา
    const sqftToCharge = priceMode === "actual" ? calcResult.actualSqft : skuSqft;

    // 🔑 3) สร้าง Variant Code อัตโนมัติ
    const autoVariantCode = isVariant ? generateVariantCode() : null;

    // 🔑 4) สร้างชื่อใหม่ (Variant / Non-Variant)
    const finalName =
      isVariant && autoVariantCode
        ? `${selectedItem.description} ${autoVariantCode}`
        : selectedItem.description;

    // 5) สร้าง item object
    const itemToAdd = {
      // --- identity ---
      sku: selectedItem.sku,
      name: finalName,
      category: "G",
      isGlass: true,
      isVariant,

      product_group: selectedItem.product_group ?? null,
      product_sub_group: selectedItem.product_sub_group ?? null,

      // --- quantity / area ---
      qty: Number(qtyCustomer), // จำนวนแผ่น
      sqft_sheet: Number(sqftPerPiece), // ⭐ เก็บ sqft_sheet ตามปกติ
      skuSqft,
      unit: selectedItem.unit || "แผ่น", // ⭐ ใช้หน่วยจาก Item_Master

      // --- cut / variant meta ---
      variantCode: autoVariantCode,
      widthRaw: calcResult.widthRaw,
      heightRaw: calcResult.heightRaw,
      widthRounded: calcResult.widthRounded,
      heightRounded: calcResult.heightRounded,

      // --- flags ---
      priceMode,
      isDraftItem: false,
      isSoldByPack, // ⭐ เพิ่ม flag เพื่อบอก backend ว่าต้องคิดราคาแบบสินค้าปกติ
    };

    // 6) เพิ่มลงรายการ
    setSelectedItems((prev) => [...prev, itemToAdd]);

    // 7) รีเซ็ตเฉพาะฟอร์มขนาด (ไม่รีเซ็ต selectedItem เพื่อให้เลือกขนาดอื่นได้ต่อ)
    if (isVariant) {
      // สำหรับ variant: รีเซ็ตเฉพาะขนาด
      setWidth("");
      setHeight("");
      setQtyCustomer(1);
      setCalcResult(null);
      // ⭐ ไม่รีเซ็ต selectedItem และ unit เพื่อให้เลือกขนาดอื่นของ SKU เดียวกันได้
    } else {
      // สำหรับ non-variant: รีเซ็ตทั้งหมด
      setSelectedItem(null);
      setWidth("");
      setHeight("");
      setQtyCustomer(1);
      setCalcResult(null);
    }
  }

  // -------------------------
  // REMOVE FROM LIST
  // -------------------------
  function handleRemoveFromList(index) {
    setSelectedItems((prev) => prev.filter((_, i) => i !== index));
  }

  // -------------------------
  // CLEAR ALL
  // -------------------------
  function handleClearAll() {
    setSelectedItems([]);
    setSelectedItem(null);
    setWidth("");
    setHeight("");
    setQtyCustomer(1);
    setCalcResult(null);
  }

  // -------------------------
  // CONFIRM ALL
  // -------------------------
  function handleConfirmAll() {
    if (selectedItems.length === 0) return;

    selectedItems.forEach((item) => {
      onConfirm(item);
    });

    setSelectedItems([]);
    onClose();
  }

  // -------------------------
  // RENDER UI
  // -------------------------
  if (!open) return null;

  // ⚡ backend กรองให้แล้ว ไม่ต้องกรองฝั่ง client
  const filteredList = glassList;

  // ⭐ สร้าง Variant Code อัตโนมัติ
  const generateVariantCode = () => {
    if (!width || !height) return "";
    
    // แปลงหน่วยเป็นตัวพิมพ์ใหญ่
    const unitWUpper = unitW.toUpperCase();
    const unitHUpper = unitH.toUpperCase();
    
    // ถ้าหน่วยเดียวกัน ใช้รูปแบบ "กว้างxยาวหน่วย"
    if (unitW === unitH) {
      return `${width}x${height}${unitWUpper}`;
    }
    
    // ถ้าหน่วยต่างกัน ใช้รูปแบบ "กว้างหน่วย1xยาวหน่วย2"
    return `${width}${unitWUpper}x${height}${unitHUpper}`;
  };

  const isVariantReady = () => {
    if (!isVariant) return true; // non-variant พร้อมเสมอ
    return width && height;
  };

  const brandDropdownOptions = filterOptions.brands;
  const typeDropdownOptions = filterOptions.types;
  const subGroupDropdownOptions = filterOptions.subGroups;
  const colorDropdownOptions = filterOptions.colors;
  const thicknessDropdownOptions = filterOptions.thicknesses;

  return (
    <div className="fixed inset-0 bg-black/40 flex justify-center items-center z-50 ">
      <div className="bg-white w-full max-w-6xl  h-[84vh] rounded-xl shadow-lg p-8 overflow-y-auto">
        {/* HEADER */}
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold">เลือกสินค้ากระจก</h2>
          <button className="text-red-600 font-bold" onClick={onClose}>
            X
          </button>
        </div>

        {/* SEARCH */}
        <input
          className="w-full border p-2 rounded my-3"
          placeholder="ค้นหา SKU / รหัส 2 / ชื่อสินค้า / SubGroup..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {/* FILTERS */}
        <div className="flex items-end gap-3 mb-4">
          <CustomDropdown
            label="Brand"
            value={brandFilter || null}
            options={brandDropdownOptions}
            onChange={(v) => setBrandFilter(v || "")}
            width={200}
          />

          <CustomDropdown
            label="Group"
            value={typeFilter || null}
            options={typeDropdownOptions}
            onChange={(v) => setTypeFilter(v || "")}
            width={200}
          />

          <CustomDropdown
            label="SubGroup"
            value={subGroupFilter || null}
            options={subGroupDropdownOptions}
            onChange={(v) => setSubGroupFilter(v || "")}
            width={360}
          />

          <CustomDropdown
            label="Color"
            value={colorFilter || null}
            options={colorDropdownOptions}
            onChange={(v) => setColorFilter(v || "")}
            width={160}
          />

          <CustomDropdown
            label="Thickness"
            value={thickFilter || null}
            options={thicknessDropdownOptions}
            onChange={(v) => setThickFilter(v || "")}
            width={120}
          />

          
        </div>
        <button
            onClick={() => {
              setBrandFilter("");
              setTypeFilter("");
              setSubGroupFilter("");
              setColorFilter("");
              setThickFilter("");
              setSearch("");
            }}
            className="px-2 py-2 h-8 mb-2 border rounded-lg hover:bg-gray-100 text-xs font-medium"
          >
            Clear All
          </button>

        {/* VARIANT CHECKBOX (เพิ่มใหม่) */}
        <div className="mb-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={variantOnly}
              onChange={(e) => setVariantOnly(e.target.checked)}
            />
            แสดงเฉพาะสินค้า รหัสกลุ่ม
          </label>
        </div>

        {/* SKU TABLE */}
        <div 
          className="border rounded-lg max-h-[360px] overflow-y-auto mb-4"
          onScroll={(e) => {
            const el = e.currentTarget;
            const nearBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 50;

            if (nearBottom && hasMore && !loadingMore) {
              loadGlass(false, search);
            }
          }}
        >
          {loading && glassList.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mb-3"></div>
              <p className="text-sm text-gray-600">กำลังโหลดข้อมูลกระจก...</p>
            </div>
          ) : filteredList.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>ไม่พบสินค้าที่ตรงกับเงื่อนไข</p>
            </div>
          ) : (
            <>
              <table className="w-full text-sm">
                <thead className="bg-gray-100 sticky top-0 z-10 border-b shadow-sm">
                  <tr className="grid grid-cols-12 gap-2 text-gray-700 font-semibold">
                    <th className="col-span-2 p-2 text-left">SKU</th>
                    <th className="col-span-4 p-2 text-left">ชื่อสินค้า</th>
                    <th className="col-span-2 p-2 text-left">SubGroup</th>
                    <th className="col-span-2 p-2 text-center">ขนาด (นิ้ว)</th>
                    <th className="col-span-1 p-2 text-center">หนา</th>
                    <th className="col-span-1 p-2 text-center">สต๊อก</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredList.map((item, idx) => (
                    <GlassTableRow
                      key={`${item.sku}-${idx}`}
                      item={item}
                      isActive={selectedItem?.sku === item.sku}
                      onClick={() => setSelectedItem(item)}
                      stockData={stockData}
                    />
                  ))}
                </tbody>
              </table>

              {/* Loading indicator สำหรับโหลดเพิ่ม */}
              {loadingMore && (
                <div className="flex justify-center py-3">
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    กำลังโหลดเพิ่ม...
                  </div>
                </div>
              )}

              {/* แสดงว่าโหลดครบแล้ว */}
              {!hasMore && filteredList.length > 0 && (
                <div className="text-xs text-gray-400 text-center py-3 border-t mt-2">
                  โหลดครบแล้ว
                </div>
              )}
            </>
          )}
          
          {/* แสดงจำนวนผลลัพธ์ */}
          {!loading && filteredList.length > 0 && (
            <div className="text-xs text-gray-500 text-center mt-2 pt-2 border-t">
              แสดง {filteredList.length} รายการ
              {total > 0 && ` จากทั้งหมด ${total} รายการ`}
            </div>
          )}
        </div>

        {/* SIZE SECTION */}
        {selectedItem && isVariant && (
          <div className="border rounded p-3 mb-3 bg-blue-50">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-blue-900">
                กำลังเลือก: {selectedItem.description}
              </h3>
              <button
                onClick={() => {
                  setSelectedItem(null);
                  setWidth("");
                  setHeight("");
                  setQtyCustomer(1);
                  setCalcResult(null);
                  setIsSoldByPack(false);
                }}
                className="text-xs px-2 py-1 border rounded hover:bg-white"
              >
                เปลี่ยน SKU
              </button>
            </div>

            {/* ⭐ CHECKBOX: ขายยกแพ็ก/แผ่น */}
            <div className="mb-3 p-2 bg-white rounded border border-blue-200">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={isSoldByPack}
                  onChange={(e) => setIsSoldByPack(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="font-medium">ขายยกลัง (กรุณากดเลือก)</span>
              </label>
            </div>

            {/* ⭐ แสดง Variant Code ที่จะถูกสร้าง */}
            {width && height && (
              <div className="mb-3 p-2 bg-white rounded border border-blue-200">
                <div className="text-xs text-gray-600 mb-1">Variant Code ที่จะสร้าง:</div>
                <div className="text-sm font-semibold text-blue-700">
                  {generateVariantCode()}
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              {/* WIDTH */}
              <div>
                <label className="text-sm font-medium">กว้าง</label>
                <div className="flex gap-2">
                  <input
                    className="border p-2 w-full rounded"
                    type="number"
                    placeholder="เช่น 1000"
                    value={width}
                    onChange={(e) => setWidth(e.target.value)}
                  />
                  <select
                    className="border p-2 rounded"
                    value={unitW}
                    onChange={(e) => {
                      setUnitW(e.target.value);
                      setUnitH(e.target.value); // ⭐ เปลี่ยนหน่วยยาวตาม
                    }}
                  >
                    <option value="inch">inch</option>
                    <option value="cm">cm</option>
                    <option value="mm">mm</option>
                    <option value="ft">ft</option>
                  </select>
                </div>
              </div>

              {/* HEIGHT */}
              <div>
                <label className="text-sm font-medium">ยาว</label>
                <div className="flex gap-2">
                  <input
                    className="border p-2 w-full rounded"
                    type="number"
                    placeholder="เช่น 1200"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                  />
                  <select
                    className="border p-2 rounded"
                    value={unitH}
                    onChange={(e) => setUnitH(e.target.value)}
                  >
                    <option value="inch">inch</option>
                    <option value="cm">cm</option>
                    <option value="mm">mm</option>
                    <option value="ft">ft</option>
                  </select>
                </div>
              </div>

              {/* QTY CUSTOMER */}
              <div className="col-span-2">
                <label className="text-sm font-medium">จำนวนแผ่น</label>
                <input
                  className="border p-2 w-full rounded"
                  type="number"
                  min={1}
                  value={qtyCustomer}
                  onChange={(e) => setQtyCustomer(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {/* ---------- NON-VARIANT ---------- */}
        {selectedItem && !isVariant && (
          <div className="border rounded p-3 mb-3 bg-green-50">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-red-600">
                กำลังเลือก: {selectedItem.description}
              </h3>
              <button
                onClick={() => {
                  setSelectedItem(null);
                  setQtyCustomer(1);
                  setCalcResult(null);
                  setIsSoldByPack(false);
                }}
                className="text-xs px-2 py-1 border rounded hover:bg-white"
              >
                เปลี่ยน SKU
              </button>
            </div>

            {/* ⭐ CHECKBOX: ขายยกแพ็ก/แผ่น */}
            <div className="mb-3 p-2 bg-green-50 rounded ">
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={isSoldByPack}
                  onChange={(e) => setIsSoldByPack(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="font-medium text-lg">ขายยกลัง (กรุณากดเลือก)</span>
              </label>
            </div>

            <div>
              <label className="text-sm font-medium">จำนวนแผ่น</label>
              <input
                className="border p-2 w-full rounded"
                type="number"
                min={1}
                value={qtyCustomer}
                onChange={(e) => setQtyCustomer(e.target.value)}
              />
            </div>
          </div>
        )}

        {/* RESULT SECTION */}
        {calcResult && (
          <div className="p-4 border rounded bg-gradient-to-r from-green-50 to-blue-50 mb-3">
            <h3 className="font-bold text-green-700 mb-3">ผลการคำนวณ</h3>

            <div className="space-y-1 text-sm mb-3">
              <p>
                ขนาดปัดลงฟุตแล้ว: <span className="font-semibold">{calcResult.width} × {calcResult.height} นิ้ว</span>
              </p>
              <p>
                พื้นที่ต่อแผ่น: <span className="font-semibold">{calcResult.sqft.toFixed(2)} ตารางฟุต</span>
              </p>
              <p className="font-bold text-base">
                พื้นที่รวม ({qtyCustomer} แผ่น): <span className="text-green-700">{(calcResult.sqft * qtyCustomer).toFixed(2)} ตารางฟุต</span>
              </p>
            </div>

            {/* ADD TO LIST ACTION */}
            {selectedItem && (
              <div className="flex items-center gap-3">
                <button
                  onClick={handleAddToList}
                  disabled={!isVariantReady()}
                  className={`flex-1 px-4 py-2 rounded-lg text-white font-medium ${
                    isVariantReady()
                      ? "bg-blue-600 hover:bg-blue-700 shadow-md"
                      : "bg-gray-400 cursor-not-allowed"
                  }`}
                >
                  {isVariant ? "เพิ่มขนาดนี้ลงรายการ" : "เพิ่มลงรายการ"}
                </button>

                {isVariant && !isVariantReady() && (
                  <div className="text-xs text-gray-600">
                    * กรุณากรอกขนาดกว้างและยาวให้ครบก่อน
                  </div>
                )}
              </div>
            )}

            {isVariant && isVariantReady() && (
              <div className="text-xs text-blue-600 mt-2 bg-blue-100 p-2 rounded">
                💡 เคล็ดลับ: หลังจากเพิ่มแล้ว คุณสามารถกรอกขนาดอื่นของ SKU เดียวกันได้เลย
              </div>
            )}
          </div>
        )}

        {/* ================= SELECTED ITEMS LIST ================= */}
        {selectedItems.length > 0 && (
          <div className="border rounded-xl bg-gray-50 mt-4">
            <div className="px-4 py-2 border-b bg-white rounded-t-xl flex items-center justify-between">
              <div className="text-sm font-semibold text-gray-700">
                รายการที่เลือกแล้ว ({selectedItems.length})
              </div>
              <button
                onClick={handleClearAll}
                className="text-xs px-3 py-1 border rounded-lg hover:bg-gray-50"
              >
                ล้างทั้งหมด
              </button>
            </div>

            <div className="max-h-[200px] overflow-y-auto p-3 space-y-2">
              {selectedItems.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between bg-white border rounded-lg px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium truncate">
                      {item.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      SKU: {item.sku}
                      {item.isVariant && item.variantCode && ` (${item.variantCode})`}
                      {" • "}{item.qty} แผ่น • {item.sqft_sheet.toFixed(2)} ตร.ฟุต/แผ่น
                    </div>
                  </div>

                  <button
                    onClick={() => handleRemoveFromList(index)}
                    className="ml-3 text-sm px-3 py-1 border rounded-lg hover:bg-red-50 hover:border-red-200"
                    title="ลบรายการนี้"
                  >
                    ลบ
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================= SUMMARY BAR ================= */}
        {selectedItems.length > 0 && (
          <div className="pt-4 mt-4 border-t flex justify-between items-center bg-white">
            <div className="text-sm text-gray-700">
              เลือกแล้ว {selectedItems.length} รายการ • รวม{" "}
              {selectedItems.reduce((sum, item) => sum + item.qty, 0)} แผ่น
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleConfirmAll}
                className="px-5 py-2 bg-green-600 text-white rounded-lg
                           hover:bg-green-700 shadow"
              >
                ยืนยันรายการ
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
