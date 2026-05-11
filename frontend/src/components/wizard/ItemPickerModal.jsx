import React, { useState, useEffect, useMemo } from "react";
import api from "../../services/api.js";
import Loader from "../Loader.jsx";
import ItemCard from "./ItemCard.jsx";
import AluminiumPicker from "./AluminiumPicker.jsx";
import CLinePicker from "./CLinePicker.jsx";
import AccessoriesPicker from "./AccessoriesPicker.jsx";
import SealantPicker from "./SealantPicker.jsx";
import GypsumPicker from "./GypsumPicker.jsx";

function ItemPickerModal({ open, category, onClose, onConfirm }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false); // ⭐ แยก loading สำหรับโหลดเพิ่ม
  const [searchTerm, setSearchTerm] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);


  // ⭐ state สำหรับ multi-add summary
  const [selectedItems, setSelectedItems] = useState([]);
  // ⭐ item ที่ user คลิกอยู่
  const [activeItem, setActiveItem] = useState(null);
  // ⭐ related items - โหลดแยกจาก backend
  const [relatedItems, setRelatedItems] = useState([]);
  const [loadingRelated, setLoadingRelated] = useState(false);


  // ---------------- Filters ----------------
  const [aluFilter, setAluFilter] = useState({
    brand: null,
    group: null,
    subGroup: null,
    color: null,
    thickness: null,
  });

  const [clineFilter, setClineFilter] = useState({
    brand: null,
    group: null,
    subGroup: null,
    color: null,
    thickness: null,
  });

  const [accFilter, setAccFilter] = useState({
    brand: null,
    group: null,
    subGroup: null,
    color: null,
    character: null,
  });

  const [sealantFilter, setSealantFilter] = useState({
    brand: null,
    group: null,
    subGroup: null,
    color: null,
  });

  const [gypsumFilter, setGypsumFilter] = useState({
    brand: null,
    group: null,
    subGroup: null,
    color: null,
    thickness: null,
  });


  const loadItems = async (reset = false, searchQuery = "") => {
    if (!hasMore && !reset) return;

    // ⭐ แยก loading state
    if (reset) {
      setLoading(true);
    } else {
      if (loadingMore) return; // ป้องกันโหลดซ้ำ
      setLoadingMore(true);
    }

    const currentOffset = reset ? 0 : offset;

    try {
      // ⭐ สร้าง filter params ตาม category
      const filterParams = {};
      
      if (category === "A") {
        if (aluFilter.brand) filterParams.brand = aluFilter.brand;
        if (aluFilter.group) filterParams.group = aluFilter.group;
        if (aluFilter.subGroup) filterParams.subGroup = aluFilter.subGroup;
        if (aluFilter.color) filterParams.color = aluFilter.color;
        if (aluFilter.thickness) filterParams.thickness = aluFilter.thickness;
      } else if (category === "C") {
        if (clineFilter.brand) filterParams.brand = clineFilter.brand;
        if (clineFilter.group) filterParams.group = clineFilter.group;
        if (clineFilter.subGroup) filterParams.subGroup = clineFilter.subGroup;
        if (clineFilter.color) filterParams.color = clineFilter.color;
        if (clineFilter.thickness) filterParams.thickness = clineFilter.thickness;
      } else if (category === "E") {
        if (accFilter.brand) filterParams.brand = accFilter.brand;
        if (accFilter.group) filterParams.group = accFilter.group;
        if (accFilter.subGroup) filterParams.subGroup = accFilter.subGroup;
        if (accFilter.color) filterParams.color = accFilter.color;
        if (accFilter.character) filterParams.character = accFilter.character;
      } else if (category === "S") {
        if (sealantFilter.brand) filterParams.brand = sealantFilter.brand;
        if (sealantFilter.group) filterParams.group = sealantFilter.group;
        if (sealantFilter.subGroup) filterParams.subGroup = sealantFilter.subGroup;
        if (sealantFilter.color) filterParams.color = sealantFilter.color;
      } else if (category === "Y") {
        if (gypsumFilter.brand) filterParams.brand = gypsumFilter.brand;
        if (gypsumFilter.group) filterParams.group = gypsumFilter.group;
        if (gypsumFilter.subGroup) filterParams.subGroup = gypsumFilter.subGroup;
        if (gypsumFilter.color) filterParams.color = gypsumFilter.color;
        if (gypsumFilter.thickness) filterParams.thickness = gypsumFilter.thickness;
      }

      // ⭐ เพิ่ม search parameter
      if (searchQuery && searchQuery.trim()) {
        filterParams.search = searchQuery.trim();
      }

      const res = await api.get(
        `/api/items/categories/${category}/list`,
        {
          params: {
            limit: 10,
            offset: currentOffset,
            ...filterParams, // ⭐ ส่ง filter + search ไปด้วย
            include_product_group: true, // ⭐ ขอ product_group มาด้วย
          },
        }
      );

      const newItems = res.data.items || [];
      const total = res.data.total || 0;

      setItems((prev) =>
        reset ? newItems : [...prev, ...newItems]
      );

      const newOffset = currentOffset + newItems.length;
      setOffset(newOffset);
      
      // ⭐ เช็คจาก total แทน
      setHasMore(newOffset < total);
    } catch (err) {
      console.error("Load items error:", err);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    if (!open || !category) return;

    setItems([]);
    setOffset(0);
    setHasMore(true);
    setActiveItem(null);
    setRelatedItems([]);
    setSearchTerm("");

    loadItems(true); // ⭐ reset + โหลดชุดแรก
  }, [open, category]);

  // ⭐ เมื่อ filter เปลี่ยน ให้โหลดใหม่
  useEffect(() => {
    if (!open || !category) return;

    setItems([]);
    setOffset(0);
    setHasMore(true);
    loadItems(true, searchTerm);
  }, [aluFilter, clineFilter, accFilter, sealantFilter, gypsumFilter]);

  // ⭐ เมื่อ search term เปลี่ยน ให้โหลดใหม่ (debounce 500ms)
  useEffect(() => {
    if (!open || !category) return;

    const timer = setTimeout(() => {
      setItems([]);
      setOffset(0);
      setHasMore(true);
      loadItems(true, searchTerm);
    }, 500); // รอ 500ms หลังจากพิมพ์เสร็จ

    return () => clearTimeout(timer);
  }, [searchTerm]);


  // ---------------- Filtered items ----------------
  // ไม่ต้อง filter ฝั่ง client แล้ว เพราะ backend filter ให้แล้ว
  const filteredItems = items;

  //โหลด related items แยกจาก backend (เร็ว) + ส่ง filter ไปด้วย
  const loadRelatedItems = async (item) => {
    if (!item?.product_group) {
      setRelatedItems([]);
      return;
    }

    setLoadingRelated(true);
    try {
      // ⭐ สร้าง filter params ตาม category
      const filterParams = {};
      
      if (category === "A") {
        if (aluFilter.brand) filterParams.brand = aluFilter.brand;
        if (aluFilter.group) filterParams.group = aluFilter.group;
        if (aluFilter.subGroup) filterParams.subGroup = aluFilter.subGroup;
        if (aluFilter.color) filterParams.color = aluFilter.color;
        if (aluFilter.thickness) filterParams.thickness = aluFilter.thickness;
      } else if (category === "C") {
        if (clineFilter.brand) filterParams.brand = clineFilter.brand;
        if (clineFilter.group) filterParams.group = clineFilter.group;
        if (clineFilter.subGroup) filterParams.subGroup = clineFilter.subGroup;
        if (clineFilter.color) filterParams.color = clineFilter.color;
        if (clineFilter.thickness) filterParams.thickness = clineFilter.thickness;
      } else if (category === "E") {
        if (accFilter.brand) filterParams.brand = accFilter.brand;
        if (accFilter.group) filterParams.group = accFilter.group;
        if (accFilter.subGroup) filterParams.subGroup = accFilter.subGroup;
        if (accFilter.color) filterParams.color = accFilter.color;
        if (accFilter.character) filterParams.character = accFilter.character;
      } else if (category === "S") {
        if (sealantFilter.brand) filterParams.brand = sealantFilter.brand;
        if (sealantFilter.group) filterParams.group = sealantFilter.group;
        if (sealantFilter.subGroup) filterParams.subGroup = sealantFilter.subGroup;
        if (sealantFilter.color) filterParams.color = sealantFilter.color;
      } else if (category === "Y") {
        if (gypsumFilter.brand) filterParams.brand = gypsumFilter.brand;
        if (gypsumFilter.group) filterParams.group = gypsumFilter.group;
        if (gypsumFilter.subGroup) filterParams.subGroup = gypsumFilter.subGroup;
        if (gypsumFilter.color) filterParams.color = gypsumFilter.color;
        if (gypsumFilter.thickness) filterParams.thickness = gypsumFilter.thickness;
      }

      const res = await api.get(`/api/items/related/${item.sku || item.SKU}`, {
        params: {
          category,  // ⭐ ส่ง category ไปด้วย
          ...filterParams
        }
      });
      setRelatedItems(res.data.items || []);
    } catch (err) {
      console.error("Load related items error:", err);
      setRelatedItems([]);
    } finally {
      setLoadingRelated(false);
    }
  };

  // ---------------- Add to summary (แทนการปิด modal) ----------------
  const handleAdd = async (item, qty) => {
  try {
    const sku = item.sku || item.SKU;

  // ⭐ โหลด detail + enrich
    const res = await api.get(`/api/items/${sku}`);
    const fullItem = res.data;

    setActiveItem(fullItem);
    
    // ⭐ โหลด related items แยก
    loadRelatedItems(fullItem);

    const normalizedItem = {
      ...fullItem,
      unit:
        fullItem.unit ||
        fullItem["Base_Unit_of_Measure"] ||
        fullItem.saleUnit ||
        "-",
      pkg_size: fullItem.pkg_size ?? 1,
      product_weight: fullItem.product_weight ?? 0,
      product_group: fullItem.product_group ?? null,
      product_sub_group: fullItem.product_sub_group ?? null,
      stock: fullItem.stock || null, // ⭐ เพิ่มข้อมูล stock
    };

    setSelectedItems((prev) => {
      const exist = prev.find((x) => x.sku === sku);
      if (exist) {
        return prev.map((x) =>
          x.sku === sku ? { ...x, qty: x.qty + qty } : x
        );
      }
      return [...prev, { sku, item: normalizedItem, qty }];
    });
  } catch (err) {
    console.error("load item detail error:", err);
  }
};


  // ---------------- Remove one from summary ----------------
  const handleRemoveSelected = (sku) => {
    setSelectedItems((prev) => prev.filter((x) => x.sku !== sku));
  };

  // ---------------- Clear all (and reset related) ----------------
  const handleClearAll = () => {
    setSelectedItems([]);
    setActiveItem(null);
    setRelatedItems([]);
  };


  // ---------------- Confirm all ----------------
  const handleConfirmAll = () => {
    if (!onConfirm || selectedItems.length === 0) return;

    selectedItems.forEach(({ item, qty }) => {
      onConfirm(item, qty); // ⭐ interface เดิม
    });

    setSelectedItems([]);
    onClose();
  };

  if (!open) return null;

  return (
  <div className="fixed inset-0 z-50 bg-black/50 p-4 flex">
    <div
        className="w-full max-w-6xl bg-white rounded-2xl shadow-2xl
                  max-h-[90vh] flex flex-col p-6
                  mx-auto "
        onClick={(e) => e.stopPropagation()}
      >

      {/* ================= HEADER ================= */}
      <div className="flex justify-between items-center pb-4 border-b shrink-0">
        <h2 className="text-xl font-bold">
          เลือกสินค้า <span className="text-gray-400">({category})</span>
        </h2>
        <button
          onClick={() => {
            handleClearAll();
            onClose();
          }}

          className="text-gray-500 hover:text-black"
        >
          ✕
        </button>
      </div>

      {/* ================= BODY ================= */}
      <div className="mt-4 flex-1 min-h-0 flex flex-col gap-4">
        {/* SEARCH */}
        <input
          type="search"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder={`ค้นหาในหมวด ${category}`}
          className="w-full rounded-xl border px-4 py-3
                     focus:ring-2 focus:ring-blue-200 outline-none"
        />

        {/* FILTERS */}
        <div className="shrink-0">
          {category === "A" && <AluminiumPicker onSelect={setAluFilter} />}
          {category === "C" && <CLinePicker onSelect={setClineFilter} />}
          {category === "E" && <AccessoriesPicker onSelect={setAccFilter} />}
          {category === "S" && <SealantPicker onSelect={setSealantFilter} />}
          {category === "Y" && <GypsumPicker onSelect={setGypsumFilter} />}
        </div>

        {/* CONTENT */}
        <div className="flex-1 min-h-0 overflow-hidden relative">
            {/* 🔥 Loader แสดงเฉพาะตอนโหลดครั้งแรก */}
            {loading && items.length === 0 && (
              <div className="absolute inset-0 bg-white z-20 flex items-center justify-center">
                <Loader />
              </div>
            )}

            {/* ❗ grid ต้อง render ตลอด */}
            <div className="grid grid-cols-2 gap-5 h-full min-h-0 overflow-hidden">
              {/* ================= LEFT ================= */}
              <div className="flex flex-col bg-gray-50 rounded-xl border overflow-hidden">
                <div className="px-4 py-2 text-sm font-semibold text-gray-700 border-b bg-white">
                  รายการสินค้า
                </div>

                <div
                  className="flex-1 overflow-y-auto p-4"
                  onScroll={(e) => {
                    const el = e.currentTarget;
                    const nearBottom =
                      el.scrollTop + el.clientHeight >= el.scrollHeight - 50;

                    if (nearBottom && hasMore && !loadingMore) {
                      loadItems(false, searchTerm); // ⭐ โหลดเพิ่มพร้อม search term
                    }
                  }}
                >
                  <div className="grid grid-cols-1 gap-4">
                    {filteredItems.map((item, idx) => (
                      <ItemCard
                        key={`${item.sku || item.SKU}-${idx}`}
                        item={item}
                        onAdd={handleAdd}
                      />
                    ))}

                    {/* ⭐ แสดง loading indicator เล็กๆ ตอนโหลดเพิ่ม */}
                    {loadingMore && (
                      <div className="flex justify-center py-4">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                          กำลังโหลด...
                        </div>
                      </div>
                    )}

                    {/* hint ว่าโหลดครบแล้ว */}
                    {!hasMore && filteredItems.length > 0 && (
                      <div className="text-xs text-gray-400 text-center py-4">
                        โหลดครบแล้ว
                      </div>
                    )}

                    {/* ไม่มีสินค้า */}
                    {!loading && filteredItems.length === 0 && (
                      <div className="text-sm text-gray-400 text-center py-10">
                        ไม่พบสินค้า
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* ================= RIGHT ================= */}
              <div className="flex flex-col bg-gray-50 rounded-xl border overflow-hidden">
                <div className="px-4 py-2 text-sm font-semibold text-gray-700 border-b bg-white">
                  สินค้าในกลุ่มเดียวกัน
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                  {/* Loading state */}
                  {loadingRelated && (
                    <div className="flex justify-center py-10">
                      <div className="flex items-center gap-2 text-sm text-gray-500">
                        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        กำลังโหลด...
                      </div>
                    </div>
                  )}

                  {!loadingRelated && !activeItem && (
                    <div className="text-sm text-gray-400 text-center mt-10">
                      เลือกสินค้าเพื่อดูรายการที่เกี่ยวข้อง
                    </div>
                  )}

                  {!loadingRelated && activeItem && relatedItems.length === 0 && (
                    <div className="text-sm text-gray-400 text-center mt-10">
                      ไม่พบสินค้าใน Product Group เดียวกัน
                    </div>
                  )}

                  {!loadingRelated && (
                    <div className="grid grid-cols-1 gap-4">
                      {relatedItems.map((item, idx) => (
                        <ItemCard
                          key={`related-${item.sku || item.SKU}-${idx}`}
                          item={item}
                          onAdd={handleAdd}
                        />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>              

      {/* ================= ADDED ITEMS LIST ================= */}
      {selectedItems.length > 0 && (
        <div className="border rounded-xl bg-gray-50 mt-4 h-[180px]">
          <div className="px-4 py-2 border-b bg-blue-600 rounded-t-xl flex items-center justify-between">
            <div className="text-sm font-semibold text-white">
              รายการที่เพิ่มแล้ว ({selectedItems.length})
            </div>
            <button
              onClick={handleClearAll}
              className="text-xs px-3 py-1 border rounded-lg hover:bg-blue-700 text-white"
            >
              ล้างทั้งหมด
            </button>
          </div>

          <div className="max-h-[160px] overflow-y-auto p-3 space-y-2">
            {selectedItems.map(({ sku, item, qty }) => (
              <div
                key={sku}
                className="flex items-center justify-between bg-white border rounded-lg px-3 py-2"
              >
                <div className="min-w-0">
                  <div className="text-sm font-medium truncate">
                    {item?.name || "-"}
                  </div>
                  <div className="text-xs text-gray-500 truncate">
                    SKU: {sku} • Qty: {qty} {item?.unit ? item.unit : ""}
                  </div>
                </div>

                <button
                  onClick={() => handleRemoveSelected(sku)}
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
        <div className="pt-4 border-t flex justify-between items-center shrink-0 bg-white">
          <div className="text-sm text-gray-700">
            เลือกแล้ว {selectedItems.length} รายการ • รวม{" "}
            {selectedItems.reduce((s, x) => s + x.qty, 0)} หน่วย
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

export default ItemPickerModal;
