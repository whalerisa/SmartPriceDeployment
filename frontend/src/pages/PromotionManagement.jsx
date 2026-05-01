import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Plus,
  Trash2,
  Power,
  PowerOff,
  Megaphone,
  ChevronDown,
  Check
} from 'lucide-react';
import api from '../services/api';

const CATEGORY_OPTIONS = [
  { value: 'Glass', label: 'Glass' },
  { value: 'Aluminum', label: 'Aluminum' },
  { value: 'Sealant', label: 'Sealant' },
  { value: 'Gypsum', label: 'Gypsum' },
  { value: 'C-Line', label: 'C-Line' },
  { value: 'Accessories', label: 'Accessories' }
];

const createDefaultForm = () => ({
  promotion_name: '',
  branches: ['ALL'],
  start_date: '',
  end_date: '',
  selection_type: 'items', // items | filter (removed customer)
  promotion_text: '',
  items: [],
  filter_criteria: {
    categories: [],
    brands: [],
    groups: [],
    subGroups: [],
    colors: [],
    thicknesses: []
  },
  customer_types: [] // ⭐ ประเภทลูกค้าที่ใช้โปรโมชั่นได้ (R, W, I, P) - ใช้กับทั้ง items และ filter
});

const CUSTOMER_TYPE_OPTIONS = [
  { value: 'R', label: 'R - ร้านค้าปลีก' },
  { value: 'W', label: 'W - ร้านค้าส่ง' },
  { value: 'I', label: 'I - ผู้รับเหมา' },
  { value: 'P', label: 'P - โครงการ' }
];

const emptyNewItem = { sku: '', promotion_text: '' };

const PromotionManagement = ({ standalone = false }) => {
  const [promotions, setPromotions] = useState([]);
  const [branches, setBranches] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState(createDefaultForm());
  const [newItem, setNewItem] = useState(emptyNewItem);

  const [filterOptions, setFilterOptions] = useState({
    categories: CATEGORY_OPTIONS,
    brands: [],
    groups: [],
    subGroups: [],
    colors: [],
    thicknesses: []
  });

  const [matchedSkus, setMatchedSkus] = useState([]);
  const [loadingSkus, setLoadingSkus] = useState(false);

  const [openDropdown, setOpenDropdown] = useState({});

  // ⭐ State สำหรับ SKU search
  const [skuSearchResults, setSkuSearchResults] = useState([]);
  const [skuSearchLoading, setSkuSearchLoading] = useState(false);
  const [showSkuDropdown, setShowSkuDropdown] = useState(false);

  useEffect(() => {
    loadPromotions();
    loadBranches();
  }, []);

  // ⭐ useEffect สำหรับ SKU search
  useEffect(() => {
    if (!newItem.sku || newItem.sku.length < 3) {
      setSkuSearchResults([]);
      setShowSkuDropdown(false);
      return;
    }

    const searchSKU = async () => {
      try {
        setSkuSearchLoading(true);
        const res = await api.get("/api/items/search", {
          params: { q: newItem.sku },
        });
        setSkuSearchResults(res.data || []);
        setShowSkuDropdown(true);
      } catch (e) {
        console.error(e);
        setSkuSearchResults([]);
      } finally {
        setSkuSearchLoading(false);
      }
    };

    const t = setTimeout(() => {
      searchSKU();
    }, 300);

    return () => clearTimeout(t);
  }, [newItem.sku]);

  // โหลด filter options เมื่อ categories เปลี่ยน
  useEffect(() => {
    if (formData.selection_type === 'filter') {
      loadFilterOptions();
    }
  }, [formData.filter_criteria.categories, formData.selection_type]);

  const loadPromotions = async () => {
    try {
      const response = await api.get('/api/promotions/');
      setPromotions(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Error loading promotions:', error);
      setPromotions([]);
    }
  };

  const loadBranches = async () => {
    try {
      const response = await api.get('/api/branches');
      setBranches(response.data?.branches || []);
    } catch (error) {
      console.error('Error loading branches:', error);
      setBranches([]);
    }
  };

  const loadFilterOptions = async () => {
    try {
      // ดึงข้อมูล filter options ตาม categories ที่เลือก
      const selectedCategories = formData.filter_criteria.categories || [];
      
      console.log('🔍 [LOAD FILTER] Selected categories:', selectedCategories);
      
      if (selectedCategories.length === 0) {
        // ถ้ายังไม่เลือก category ให้ reset filter options
        setFilterOptions({
          categories: CATEGORY_OPTIONS,
          brands: [],
          groups: [],
          subGroups: [],
          colors: [],
          thicknesses: []
        });
        return;
      }

      const categoryMap = {
        'Glass': 'G',
        'Aluminum': 'A',
        'Sealant': 'S',
        'Gypsum': 'Y',
        'C-Line': 'C',
        'Accessories': 'E'
      };

      const allOptions = {
        brands: new Set(),
        groups: new Set(),
        subGroups: new Set(),
        colors: new Set(),
        thicknesses: new Set()
      };

      // ดึงข้อมูลจากแต่ละ category ที่เลือก
      await Promise.all(
        selectedCategories.map(async (cat) => {
          const categoryCode = categoryMap[cat];
          console.log(`🔍 [LOAD FILTER] Processing category: ${cat} -> ${categoryCode}`);
          
          if (!categoryCode) {
            console.log(`⚠️ [LOAD FILTER] Skipping ${cat} (invalid)`);
            return;
          }

          try {
            // Glass ใช้ API แยก
            const url = categoryCode === 'G' 
              ? '/api/glass/filter-options'
              : `/api/items/categories/${categoryCode}/filter-options`;
            
            console.log(`📡 [LOAD FILTER] Fetching: ${url}`);
            
            const response = await api.get(url);
            const data = response.data;
            
            console.log(`✅ [LOAD FILTER] Response for ${categoryCode}:`, data);

            // แปลงข้อมูลจาก API format {code, name} หรือ {value, label} เป็น {value, label}
            if (data.brand || data.brands) {
              const brandData = data.brand || data.brands;
              // ถ้าเป็น array ของ {value, label} ให้ใช้เลย
              if (Array.isArray(brandData) && brandData.length > 0 && brandData[0].value) {
                brandData.forEach(b => {
                  if (b.value && b.label) {
                    allOptions.brands.add(JSON.stringify({
                      value: b.value,
                      label: b.label
                    }));
                  }
                });
              } else {
                // ถ้าเป็น array ของ {code, name}
                brandData.forEach(b => {
                  if (b.code && b.name) {
                    allOptions.brands.add(JSON.stringify({
                      value: b.code,
                      label: b.name
                    }));
                  }
                });
              }
            }
            
            // Glass ใช้ "types" แทน "group"
            if (data.group || data.types) {
              const groupData = data.group || data.types;
              if (Array.isArray(groupData) && groupData.length > 0 && groupData[0].value) {
                groupData.forEach(g => {
                  if (g.value && g.label) {
                    allOptions.groups.add(JSON.stringify({
                      value: g.value,
                      label: g.label
                    }));
                  }
                });
              } else {
                groupData.forEach(g => {
                  if (g.code && g.name) {
                    allOptions.groups.add(JSON.stringify({
                      value: g.code,
                      label: g.name
                    }));
                  }
                });
              }
            }
            
            if (data.subGroup || data.subGroups) {
              const subGroupData = data.subGroup || data.subGroups;
              if (Array.isArray(subGroupData) && subGroupData.length > 0 && subGroupData[0].value) {
                subGroupData.forEach(s => {
                  if (s.value && s.label) {
                    allOptions.subGroups.add(JSON.stringify({
                      value: s.value,
                      label: s.label
                    }));
                  }
                });
              } else {
                subGroupData.forEach(s => {
                  if (s.code && s.name) {
                    allOptions.subGroups.add(JSON.stringify({
                      value: s.code,
                      label: s.name
                    }));
                  }
                });
              }
            }
            
            if (data.color || data.colors) {
              const colorData = data.color || data.colors;
              if (Array.isArray(colorData) && colorData.length > 0 && colorData[0].value) {
                colorData.forEach(c => {
                  if (c.value && c.label) {
                    allOptions.colors.add(JSON.stringify({
                      value: c.value,
                      label: c.label
                    }));
                  }
                });
              } else {
                colorData.forEach(c => {
                  if (c.code && c.name) {
                    allOptions.colors.add(JSON.stringify({
                      value: c.code,
                      label: c.name
                    }));
                  }
                });
              }
            }
            
            if (data.thickness || data.thicknesses) {
              const thicknessData = data.thickness || data.thicknesses;
              if (Array.isArray(thicknessData) && thicknessData.length > 0 && thicknessData[0].value) {
                thicknessData.forEach(t => {
                  if (t.value && t.label) {
                    allOptions.thicknesses.add(JSON.stringify({
                      value: t.value,
                      label: t.label
                    }));
                  }
                });
              } else {
                thicknessData.forEach(t => {
                  if (t.code && t.name) {
                    allOptions.thicknesses.add(JSON.stringify({
                      value: t.code,
                      label: t.name
                    }));
                  }
                });
              }
            }
          } catch (err) {
            console.error(`❌ [LOAD FILTER] Error loading filter options for category ${categoryCode}:`, err);
          }
        })
      );

      console.log('📦 [LOAD FILTER] All options collected:', {
        brands: allOptions.brands.size,
        groups: allOptions.groups.size,
        subGroups: allOptions.subGroups.size,
        colors: allOptions.colors.size,
        thicknesses: allOptions.thicknesses.size
      });

      // แปลง Set กลับเป็น array และ parse JSON
      const finalOptions = {
        categories: CATEGORY_OPTIONS,
        brands: Array.from(allOptions.brands)
          .map(b => JSON.parse(b))
          .filter(item => item.label && item.value) // กรองเฉพาะที่มี label และ value
          .sort((a, b) => (a.label || '').localeCompare(b.label || '')),
        groups: Array.from(allOptions.groups)
          .map(g => JSON.parse(g))
          .filter(item => item.label && item.value)
          .sort((a, b) => (a.label || '').localeCompare(b.label || '')),
        subGroups: Array.from(allOptions.subGroups)
          .map(s => JSON.parse(s))
          .filter(item => item.label && item.value)
          .sort((a, b) => (a.label || '').localeCompare(b.label || '')),
        colors: Array.from(allOptions.colors)
          .map(c => JSON.parse(c))
          .filter(item => item.label && item.value)
          .sort((a, b) => (a.label || '').localeCompare(b.label || '')),
        thicknesses: Array.from(allOptions.thicknesses)
          .map(t => JSON.parse(t))
          .filter(item => item.label && item.value)
          .sort((a, b) => (a.label || '').localeCompare(b.label || ''))
      };
      
      console.log('✅ [LOAD FILTER] Final options:', finalOptions);
      setFilterOptions(finalOptions);
    } catch (error) {
      console.error('❌ [LOAD FILTER] Error loading filter options:', error);
      setFilterOptions({
        categories: CATEGORY_OPTIONS,
        brands: [],
        groups: [],
        subGroups: [],
        colors: [],
        thicknesses: []
      });
    }
  };

  const resetForm = () => {
    setFormData(createDefaultForm());
    setNewItem(emptyNewItem);
    setOpenDropdown({});
  };

  const handleBranchToggle = (branchCode) => {
    setFormData((prev) => {
      let newBranches = [...prev.branches];

      if (branchCode === 'ALL') {
        newBranches = ['ALL'];
      } else {
        newBranches = newBranches.filter((b) => b !== 'ALL');

        if (newBranches.includes(branchCode)) {
          newBranches = newBranches.filter((b) => b !== branchCode);
        } else {
          newBranches.push(branchCode);
        }

        if (newBranches.length === 0) {
          newBranches = ['ALL'];
        }
      }

      return { ...prev, branches: newBranches };
    });
  };

  const handleAddItem = () => {
    if (!newItem.sku.trim() || !newItem.promotion_text.trim()) return;

    setFormData((prev) => ({
      ...prev,
      items: [
        ...prev.items,
        {
          sku: newItem.sku.trim(),
          promotion_text: newItem.promotion_text.trim()
        }
      ]
    }));

    setNewItem(emptyNewItem);
  };

  const handleRemoveItem = (index) => {
    setFormData((prev) => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index)
    }));
  };

  const handleFilterToggle = (key, value) => {
    setFormData((prev) => {
      const current = prev.filter_criteria[key] || [];
      const exists = current.includes(value);

      return {
        ...prev,
        filter_criteria: {
          ...prev.filter_criteria,
          [key]: exists
            ? current.filter((v) => v !== value)
            : [...current, value]
        }
      };
    });
  };

  const handleCategoryToggle = (value) => {
    setFormData((prev) => {
      const current = prev.filter_criteria.categories || [];
      const exists = current.includes(value);

      const newCategories = exists
        ? current.filter((v) => v !== value)
        : [...current, value];

      // Reset filter criteria อื่นๆ เมื่อเปลี่ยน category
      return {
        ...prev,
        filter_criteria: {
          categories: newCategories,
          brands: [],
          groups: [],
          subGroups: [],
          colors: [],
          thicknesses: []
        }
      };
    });
  };

  const fetchMatchedSkus = async () => {
    if (formData.selection_type !== 'filter') return;

    const fc = formData.filter_criteria;
    const hasAnyFilter =
      fc.categories.length > 0 ||
      fc.brands.length > 0 ||
      fc.groups.length > 0 ||
      fc.subGroups.length > 0 ||
      fc.colors.length > 0 ||
      fc.thicknesses.length > 0;

    if (!hasAnyFilter) {
      setMatchedSkus([]);
      return;
    }

    setLoadingSkus(true);
    try {
      const response = await api.post('/api/promotions/get-skus-by-filter', fc);
      setMatchedSkus(response.data?.skus || []);
    } catch (error) {
      console.error('Error fetching matched SKUs:', error);
      setMatchedSkus([]);
    } finally {
      setLoadingSkus(false);
    }
  };

  // เรียก fetchMatchedSkus เมื่อ filter_criteria เปลี่ยน
  useEffect(() => {
    if (formData.selection_type === 'filter') {
      const timeoutId = setTimeout(() => {
        fetchMatchedSkus();
      }, 500); // debounce 500ms

      return () => clearTimeout(timeoutId);
    } else {
      setMatchedSkus([]);
    }
  }, [formData.filter_criteria, formData.selection_type]);

  const handleToggleCustomerType = (type) => {
    setFormData((prev) => {
      const isSelected = prev.customer_types.includes(type);
      return {
        ...prev,
        customer_types: isSelected
          ? prev.customer_types.filter((t) => t !== type)
          : [...prev.customer_types, type]
      };
    });
  };

  const validateForm = () => {
    if (!formData.promotion_name.trim()) {
      alert('กรุณากรอกชื่อโปรโมชั่น');
      return false;
    }

    if (!formData.start_date || !formData.end_date) {
      alert('กรุณาเลือกวันที่เริ่มต้นและสิ้นสุด');
      return false;
    }

    if (formData.start_date > formData.end_date) {
      alert('วันที่เริ่มต้นต้องไม่มากกว่าวันที่สิ้นสุด');
      return false;
    }

    if (formData.selection_type === 'items' && formData.items.length === 0) {
      alert('กรุณาเพิ่มสินค้าอย่างน้อย 1 รายการ');
      return false;
    }

    if (formData.selection_type === 'filter') {
      const fc = formData.filter_criteria;
      const hasAnyFilter =
        fc.categories.length > 0 ||
        fc.brands.length > 0 ||
        fc.groups.length > 0 ||
        fc.subGroups.length > 0 ||
        fc.colors.length > 0 ||
        fc.thicknesses.length > 0;

      if (!hasAnyFilter) {
        alert('กรุณาเลือกเงื่อนไขอย่างน้อย 1 รายการ');
        return false;
      }
    }

    // ⭐ ไม่บังคับเลือกประเภทลูกค้า (ถ้าไม่เลือก = ทุกประเภท)

    return true;
  };

  const buildPayload = () => {
    const payload = {
      promotion_name: formData.promotion_name,
      branches: formData.branches,
      start_date: formData.start_date,
      end_date: formData.end_date,
      selection_type: formData.selection_type,
      promotion_text: formData.promotion_text || null,
      items: [],
      filter_criteria: null,
      gen_bus: formData.customer_types.length > 0 ? formData.customer_types.join(',') : null // ⭐ บันทึกเป็น comma-separated string
    };

    if (formData.selection_type === 'items') {
      payload.items = formData.items;
    } else if (formData.selection_type === 'filter') {
      payload.filter_criteria = formData.filter_criteria;
      // แปลง matched SKUs เป็น items
      payload.items = matchedSkus.map(sku => ({
        sku: sku.sku,
        promotion_text: formData.promotion_text || 'โปรโมชั่นพิเศษ'
      }));
    }

    return payload;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setLoading(true);

    try {
      const payload = buildPayload();
      await api.post('/api/promotions/', payload);

      alert('สร้าง Promotion สำเร็จ!');
      setShowModal(false);
      resetForm();
      loadPromotions();
    } catch (error) {
      console.error('Error creating promotion:', error);
      alert('เกิดข้อผิดพลาด: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const toggleStatus = async (promotionId, currentStatus) => {
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    try {
      await api.put(`/api/promotions/${promotionId}/status?status=${newStatus}`);
      loadPromotions();
    } catch (error) {
      console.error('Error updating status:', error);
      alert('เกิดข้อผิดพลาดในการอัพเดทสถานะ');
    }
  };

  const deletePromotion = async (promotionId) => {
    if (!window.confirm('คุณต้องการลบ Promotion นี้หรือไม่?')) return;

    try {
      await api.delete(`/api/promotions/${promotionId}`);
      loadPromotions();
    } catch (error) {
      console.error('Error deleting promotion:', error);
      alert('เกิดข้อผิดพลาดในการลบ');
    }
  };

  const renderSelectionSummary = (promo) => {
    const type = promo.selection_type || promo.SelectionType || 'items';
    
    // ⭐ แสดงประเภทลูกค้า (ถ้ามี)
    const genBus = promo.gen_bus || promo.GenBus || '';
    const types = genBus ? genBus.split(',').map(t => t.trim()) : [];
    const customerTypeText = types.length > 0 ? ` | ลูกค้า: ${types.join(', ')}` : ' | ลูกค้า: ทุกประเภท';

    if (type === 'items') {
      const items = promo.items || [];
      return `SKU ${items.length} รายการ${customerTypeText}`;
    }

    if (type === 'filter') {
      let fc = promo.filter_criteria || promo.FilterCriteria || {};
      if (typeof fc === 'string') {
        try {
          fc = JSON.parse(fc);
        } catch {
          fc = {};
        }
      }

      const count =
        (fc.categories?.length || 0) +
        (fc.brands?.length || 0) +
        (fc.groups?.length || 0) +
        (fc.subGroups?.length || 0) +
        (fc.colors?.length || 0) +
        (fc.thicknesses?.length || 0);

      return `Filter ${count} เงื่อนไข${customerTypeText}`;
    }

    return '-';
  };

  const isSubmitDisabled = useMemo(() => {
    if (loading) return true;
    if (formData.selection_type === 'items') return formData.items.length === 0;
    if (formData.selection_type === 'filter') return matchedSkus.length === 0;
    return false;
  }, [
    formData.selection_type,
    formData.items.length,
    matchedSkus.length,
    loading
  ]);

  return (
    <div className={standalone ? 'p-6 max-w-7xl mx-auto' : ''}>
      {standalone && (
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <Megaphone className="w-8 h-8 text-red-600" />
            <h1 className="text-3xl font-bold text-gray-800">จัดการโปรโมชั่น</h1>
          </div>
          <button
            onClick={() => {
              resetForm();
              setShowModal(true);
            }}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            เพิ่มโปรโมชั่น
          </button>
        </div>
      )}

      {!standalone && (
        <div className="flex justify-end mb-4">
          <button
            onClick={() => {
              resetForm();
              setShowModal(true);
            }}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            เพิ่มโปรโมชั่น
          </button>
        </div>
      )}

      <div className="grid gap-4 max-h-[600px] overflow-y-auto">
        {!promotions || promotions.length === 0 ? (
          <div className="bg-white rounded-lg shadow-md p-8 text-center text-gray-500">
            ยังไม่มีโปรโมชั่น คลิก "เพิ่มโปรโมชั่น" เพื่อสร้างโปรโมชั่นใหม่
          </div>
        ) : (
          promotions.map((promo) => (
            <div key={promo.id} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-semibold text-gray-800">
                    {promo.promotion_name || promo.PromotionName}
                  </h3>

                  <p className="text-sm text-gray-600">
                    สาขา:{' '}
                    {promo.branch === 'ALL' || promo.branch?.includes?.('ALL')
                      ? 'ทุกสาขา'
                      : promo.branch || promo.BranchCode || '-'}{' '}
                    | {promo.start_date || promo.StartDate} - {promo.end_date || promo.EndDate}
                  </p>

                  <p className="text-sm text-gray-600 mt-1">
                    ประเภท: {renderSelectionSummary(promo)}
                  </p>

                  <span
                    className={`inline-block mt-2 px-3 py-1 rounded-full text-sm ${
                      promo.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {promo.status === 'active' ? 'ใช้งาน' : 'ปิดใช้งาน'}
                  </span>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => toggleStatus(promo.id, promo.status)}
                    className={`p-2 rounded-lg ${
                      promo.status === 'active'
                        ? 'bg-yellow-100 hover:bg-yellow-200 text-yellow-700'
                        : 'bg-green-100 hover:bg-green-200 text-green-700'
                    }`}
                    title={promo.status === 'active' ? 'ปิดใช้งาน' : 'เปิดใช้งาน'}
                  >
                    {promo.status === 'active' ? (
                      <PowerOff className="w-5 h-5" />
                    ) : (
                      <Power className="w-5 h-5" />
                    )}
                  </button>

                  <button
                    onClick={() => deletePromotion(promo.id)}
                    className="p-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg"
                    title="ลบ"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {(promo.items || []).length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-semibold text-gray-700">สินค้าในโปรโมชั่น ({promo.items.length} รายการ):</h4>
                  <div className="max-h-40 overflow-y-auto space-y-2">
                    {promo.items.map((item, idx) => (
                      <div key={idx} className="bg-gray-50 p-3 rounded-lg">
                        <p className="font-medium text-gray-800 truncate">
                          SKU: {item.SKU || item.sku}
                        </p>
                        <p className="text-gray-600 text-sm truncate">
                          {item.PromotionText || item.promotion_text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h2 className="text-2xl font-bold mb-4">เพิ่มโปรโมชั่นใหม่</h2>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="block text-sm font-medium mb-1">ชื่อโปรโมชั่น</label>
                  <input
                    type="text"
                    value={formData.promotion_name}
                    onChange={(e) =>
                      setFormData({ ...formData, promotion_name: e.target.value })
                    }
                    className="w-full border rounded-lg px-3 py-2"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    สาขา (เลือกได้หลายสาขา)
                  </label>
                  <div className="border rounded-lg p-3 max-h-48 overflow-y-auto">
                    <label className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.branches.includes('ALL')}
                        onChange={() => handleBranchToggle('ALL')}
                        className="w-4 h-4"
                      />
                      <span className="font-medium">ทุกสาขา</span>
                    </label>

                    <div className="border-t my-2"></div>

                    {branches.map((branch) => (
                      <label
                        key={branch.Code}
                        className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={formData.branches.includes(branch.Code)}
                          onChange={() => handleBranchToggle(branch.Code)}
                          className="w-4 h-4"
                        />
                        <span>
                          {branch.Name} ({branch.Code})
                        </span>
                      </label>
                    ))}
                  </div>

                  <p className="text-xs text-gray-500 mt-1">
                    เลือกแล้ว:{' '}
                    {formData.branches.includes('ALL')
                      ? 'ทุกสาขา'
                      : `${formData.branches.length} สาขา`}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">วันที่เริ่มต้น</label>
                    <input
                      type="date"
                      value={formData.start_date}
                      onChange={(e) =>
                        setFormData({ ...formData, start_date: e.target.value })
                      }
                      className="w-full border rounded-lg px-3 py-2"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">วันที่สิ้นสุด</label>
                    <input
                      type="date"
                      value={formData.end_date}
                      onChange={(e) =>
                        setFormData({ ...formData, end_date: e.target.value })
                      }
                      className="w-full border rounded-lg px-3 py-2"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">รูปแบบการเลือกสินค้า</label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <label
                      className={`border rounded-xl p-4 cursor-pointer ${
                        formData.selection_type === 'items'
                          ? 'border-red-500 bg-red-50'
                          : 'border-gray-200'
                      }`}
                    >
                      <input
                        type="radio"
                        name="selection_type"
                        value="items"
                        checked={formData.selection_type === 'items'}
                        onChange={(e) =>
                          setFormData({ ...formData, selection_type: e.target.value })
                        }
                        className="hidden"
                      />
                      <div className="font-semibold">เลือกเป็นราย SKU</div>
                      <div className="text-sm text-gray-500 mt-1">
                        ใช้กรณีระบุสินค้าเป็นรายการ
                      </div>
                    </label>

                    <label
                      className={`border rounded-xl p-4 cursor-pointer ${
                        formData.selection_type === 'filter'
                          ? 'border-red-500 bg-red-50'
                          : 'border-gray-200'
                      }`}
                    >
                      <input
                        type="radio"
                        name="selection_type"
                        value="filter"
                        checked={formData.selection_type === 'filter'}
                        onChange={(e) =>
                          setFormData({ ...formData, selection_type: e.target.value })
                        }
                        className="hidden"
                      />
                      <div className="font-semibold">เลือกตาม Filter</div>
                      <div className="text-sm text-gray-500 mt-1">
                        Category / Brand / Group / SubGroup / Color / Thickness
                      </div>
                    </label>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    รายละเอียดโปรโมชั่น (ถ้ามี)
                  </label>
                  <input
                    type="text"
                    value={formData.promotion_text}
                    onChange={(e) =>
                      setFormData({ ...formData, promotion_text: e.target.value })
                    }
                    placeholder="เช่น ซื้อครบรับส่วนลด / ของแถม / เงื่อนไขพิเศษ"
                    className="w-full border rounded-lg px-3 py-2"
                  />
                </div>

                {formData.selection_type === 'items' && (
                  <div className="border-t pt-4">
                    <h3 className="font-semibold mb-3">เพิ่มสินค้าแบบราย SKU</h3>

                    {/* ⭐ เลือกประเภทลูกค้า */}
                    <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                      <label className="block text-sm font-medium mb-2">
                        ประเภทลูกค้าที่ใช้โปรโมชั่นได้ (ไม่เลือก = ทุกประเภท)
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {CUSTOMER_TYPE_OPTIONS.map((option) => (
                          <label
                            key={option.value}
                            className={`border rounded-lg p-2 cursor-pointer transition-all ${
                              formData.customer_types.includes(option.value)
                                ? 'border-blue-500 bg-blue-100'
                                : 'border-gray-300 bg-white hover:border-gray-400'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={formData.customer_types.includes(option.value)}
                                onChange={() => handleToggleCustomerType(option.value)}
                                className="w-4 h-4"
                              />
                              <span className="text-sm font-medium">{option.label}</span>
                            </div>
                          </label>
                        ))}
                      </div>
                      {formData.customer_types.length > 0 && (
                        <p className="text-xs text-blue-700 mt-2">
                          เลือกแล้ว: {formData.customer_types.join(', ')}
                        </p>
                      )}
                    </div>

                    <div className="flex gap-2 mb-3 relative">
                      <div className="flex-1 relative">
                        <input
                          type="text"
                          placeholder="ค้นหา SKU หรือชื่อสินค้า (พิมพ์อย่างน้อย 3 ตัวอักษร)"
                          value={newItem.sku}
                          onChange={(e) =>
                            setNewItem({ ...newItem, sku: e.target.value })
                          }
                          className="w-full border rounded-lg px-3 py-2"
                        />
                        {/* Search results dropdown */}
                        {showSkuDropdown && newItem.sku.length >= 3 && (
                          <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-300 rounded-lg shadow-lg z-10 max-h-64 overflow-y-auto">
                            {skuSearchLoading && (
                              <div className="p-3 text-center text-gray-500">
                                กำลังค้นหา...
                              </div>
                            )}
                            {!skuSearchLoading && skuSearchResults.length === 0 && (
                              <div className="p-3 text-center text-gray-500">
                                ไม่พบสินค้า
                              </div>
                            )}
                            {!skuSearchLoading && skuSearchResults.length > 0 && (
                              skuSearchResults.map((item) => (
                                <div
                                  key={item.sku || item.id}
                                  onClick={() => {
                                    setNewItem({ ...newItem, sku: item.sku });
                                    setShowSkuDropdown(false);
                                  }}
                                  className="p-3 hover:bg-gray-100 cursor-pointer border-b last:border-b-0"
                                >
                                  <p className="font-medium text-sm">{item.sku}</p>
                                  <p className="text-xs text-gray-600">{item.name}</p>
                                </div>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                      <input
                        type="text"
                        placeholder="รายละเอียดโปรโมชั่น"
                        value={newItem.promotion_text}
                        onChange={(e) =>
                          setNewItem({ ...newItem, promotion_text: e.target.value })
                        }
                        className="flex-1 border rounded-lg px-3 py-2"
                      />
                      <button
                        type="button"
                        onClick={handleAddItem}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
                      >
                        <Plus className="w-5 h-5" />
                      </button>
                    </div>

                    <div className="space-y-2">
                      {formData.items.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 bg-gray-50 p-3 rounded-lg"
                        >
                          <div className="flex-1">
                            <p className="font-medium">{item.sku}</p>
                            <p className="text-sm text-gray-600">
                              {item.promotion_text}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(idx)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <Trash2 className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {formData.selection_type === 'filter' && (
                  <div className="border-t pt-4">
                    <h3 className="font-semibold mb-3">เลือกตามเงื่อนไขสินค้า</h3>

                    {/* ⭐ เลือกประเภทลูกค้า */}
                    <div className="mb-4 p-4 bg-blue-50 rounded-lg">
                      <label className="block text-sm font-medium mb-2">
                        ประเภทลูกค้าที่ใช้โปรโมชั่นได้ (ไม่เลือก = ทุกประเภท)
                      </label>
                      <div className="grid grid-cols-2 gap-2">
                        {CUSTOMER_TYPE_OPTIONS.map((option) => (
                          <label
                            key={option.value}
                            className={`border rounded-lg p-2 cursor-pointer transition-all ${
                              formData.customer_types.includes(option.value)
                                ? 'border-blue-500 bg-blue-100'
                                : 'border-gray-300 bg-white hover:border-gray-400'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <input
                                type="checkbox"
                                checked={formData.customer_types.includes(option.value)}
                                onChange={() => handleToggleCustomerType(option.value)}
                                className="w-4 h-4"
                              />
                              <span className="text-sm font-medium">{option.label}</span>
                            </div>
                          </label>
                        ))}
                      </div>
                      {formData.customer_types.length > 0 && (
                        <p className="text-xs text-blue-700 mt-2">
                          เลือกแล้ว: {formData.customer_types.join(', ')}
                        </p>
                      )}
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium mb-2">
                          Category (เลือกประเภทสินค้า) <span className="text-red-500">*</span>
                        </label>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                          {filterOptions.categories.map((cat) => (
                            <label
                              key={cat.value}
                              className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                                formData.filter_criteria.categories.includes(cat.value)
                                  ? 'border-red-500 bg-red-50'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              <input
                                type="checkbox"
                                checked={formData.filter_criteria.categories.includes(cat.value)}
                                onChange={() => handleCategoryToggle(cat.value)}
                                className="mr-2"
                              />
                              <span className="font-medium">{cat.label}</span>
                            </label>
                          ))}
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                          เลือก Category ก่อน จากนั้นจึงจะสามารถเลือก Brand, Group ฯลฯ ได้
                        </p>
                      </div>

                      {formData.filter_criteria.categories.length > 0 && (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <MultiSelectDropdown
                            label="Brand"
                            options={filterOptions.brands}
                            selectedValues={formData.filter_criteria.brands}
                            onToggle={(value) => handleFilterToggle('brands', value)}
                            isOpen={openDropdown.brands}
                            onOpen={() => setOpenDropdown(prev => ({ ...prev, brands: true }))}
                            onClose={() => setOpenDropdown(prev => ({ ...prev, brands: false }))}
                          />

                          <MultiSelectDropdown
                            label="Group"
                            options={filterOptions.groups}
                            selectedValues={formData.filter_criteria.groups}
                            onToggle={(value) => handleFilterToggle('groups', value)}
                            isOpen={openDropdown.groups}
                            onOpen={() => setOpenDropdown(prev => ({ ...prev, groups: true }))}
                            onClose={() => setOpenDropdown(prev => ({ ...prev, groups: false }))}
                          />

                          <MultiSelectDropdown
                            label="SubGroup"
                            options={filterOptions.subGroups}
                            selectedValues={formData.filter_criteria.subGroups}
                            onToggle={(value) => handleFilterToggle('subGroups', value)}
                            isOpen={openDropdown.subGroups}
                            onOpen={() => setOpenDropdown(prev => ({ ...prev, subGroups: true }))}
                            onClose={() => setOpenDropdown(prev => ({ ...prev, subGroups: false }))}
                          />

                          <MultiSelectDropdown
                            label="Color"
                            options={filterOptions.colors}
                            selectedValues={formData.filter_criteria.colors}
                            onToggle={(value) => handleFilterToggle('colors', value)}
                            isOpen={openDropdown.colors}
                            onOpen={() => setOpenDropdown(prev => ({ ...prev, colors: true }))}
                            onClose={() => setOpenDropdown(prev => ({ ...prev, colors: false }))}
                          />

                          <MultiSelectDropdown
                            label="Thickness"
                            options={filterOptions.thicknesses}
                            selectedValues={formData.filter_criteria.thicknesses}
                            onToggle={(value) => handleFilterToggle('thicknesses', value)}
                            isOpen={openDropdown.thicknesses}
                            onOpen={() => setOpenDropdown(prev => ({ ...prev, thicknesses: true }))}
                            onClose={() => setOpenDropdown(prev => ({ ...prev, thicknesses: false }))}
                          />
                        </div>
                      )}

                      {loadingSkus && (
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                          <p className="text-blue-700">กำลังค้นหา SKU ที่ตรงกับเงื่อนไข...</p>
                        </div>
                      )}

                      {!loadingSkus && matchedSkus.length > 0 && (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                          <p className="text-green-800 font-semibold mb-2">
                            ✅ พบ {matchedSkus.length} SKU ที่ตรงกับเงื่อนไข
                          </p>
                          <div className="max-h-48 overflow-y-auto space-y-1">
                            {matchedSkus.slice(0, 10).map((item) => (
                              <p key={item.sku} className="text-sm text-gray-700">
                                • {item.sku} - {item.description}
                              </p>
                            ))}
                            {matchedSkus.length > 10 && (
                              <p className="text-sm text-gray-500 italic">
                                ... และอีก {matchedSkus.length - 10} รายการ
                              </p>
                            )}
                          </div>
                        </div>
                      )}

                      {!loadingSkus && matchedSkus.length === 0 && (
                        formData.filter_criteria.categories.length > 0 ||
                        formData.filter_criteria.brands.length > 0 ||
                        formData.filter_criteria.groups.length > 0 ||
                        formData.filter_criteria.subGroups.length > 0 ||
                        formData.filter_criteria.colors.length > 0 ||
                        formData.filter_criteria.thicknesses.length > 0
                      ) && (
                        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                          <p className="text-yellow-800">ไม่พบ SKU ที่ตรงกับเงื่อนไขที่เลือก</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}



                <div className="flex gap-2 justify-end pt-4 border-t">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      resetForm();
                    }}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                  >
                    ยกเลิก
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitDisabled}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg disabled:opacity-50"
                  >
                    {loading ? 'กำลังบันทึก...' : 'บันทึก'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function MultiSelectDropdown({
  label,
  options = [],
  selectedValues = [],
  onToggle,
  isOpen,
  onOpen,
  onClose
}) {
  const ref = useRef(null);

  // Debug: แสดงข้อมูลที่ได้รับ
  useEffect(() => {
    console.log(`[${label}] Options:`, options.length, 'items');
    console.log(`[${label}] Selected:`, selectedValues);
  }, [label, options, selectedValues]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        onClose?.();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const selectedLabels = options
    .filter((opt) => selectedValues.includes(opt.value))
    .map((opt) => opt.label);

  const handleItemClick = (e, value) => {
    e.stopPropagation(); // ป้องกันไม่ให้ dropdown ปิด
    console.log(`[${label}] Toggling value:`, value);
    onToggle(value);
  };

  const handleButtonClick = () => {
    if (isOpen) {
      onClose();
    } else {
      onOpen();
    }
  };

  return (
    <div className="relative" ref={ref}>
      <label className="block text-sm font-medium mb-1">{label}</label>

      <button
        type="button"
        onClick={handleButtonClick}
        className="w-full border rounded-lg px-3 py-2 flex items-center justify-between bg-white hover:border-gray-400 transition-colors"
      >
        <span className="text-sm text-left truncate">
          {selectedLabels.length > 0
            ? `${selectedLabels.length} รายการที่เลือก`
            : `เลือก ${label}`}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {selectedValues.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {selectedLabels.slice(0, 5).map((text) => (
            <span
              key={text}
              className="bg-red-50 text-red-700 text-xs px-2 py-1 rounded-full"
            >
              {text}
            </span>
          ))}
          {selectedLabels.length > 5 && (
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">
              +{selectedLabels.length - 5} อื่นๆ
            </span>
          )}
        </div>
      )}

      {isOpen && (
        <div className="absolute z-20 mt-2 w-full bg-white border rounded-lg shadow-lg">
          <div className="max-h-64 overflow-y-auto">
            {options.length === 0 ? (
              <div className="p-3 text-sm text-gray-500">ไม่มีข้อมูล</div>
            ) : (
              options.map((opt) => {
                const checked = selectedValues.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={(e) => handleItemClick(e, opt.value)}
                    className={`w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center justify-between transition-colors ${
                      checked ? 'bg-red-50' : ''
                    }`}
                  >
                    <span className="text-sm flex-1">{opt.label}</span>
                    {checked && <Check className="w-4 h-4 text-green-600 flex-shrink-0 ml-2" />}
                  </button>
                );
              })
            )}
          </div>
          
          {/* ปุ่มปิด dropdown */}
          <div className="border-t p-2 bg-gray-50">
            <button
              type="button"
              onClick={onClose}
              className="w-full px-3 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
            >
              เสร็จสิ้น ({selectedValues.length} รายการ)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default PromotionManagement;