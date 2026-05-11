import React, { useState, useEffect, useRef } from 'react';
import { Plus, Trash2, Calendar, User, Building2, Filter, ChevronDown, Check } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../hooks/useAuth';

const CATEGORY_OPTIONS = [
  { value: 'Glass', label: 'Glass' },
  { value: 'Aluminum', label: 'Aluminum' },
  { value: 'Sealant', label: 'Sealant' },
  { value: 'Gypsum', label: 'Gypsum' },
  { value: 'C-Line', label: 'C-Line' },
  { value: 'Accessories', label: 'Accessories' }
];

const UNIT_OPTIONS = [
  { value: 'ตารางฟุต', label: 'ตารางฟุต' },
  { value: 'หลอด', label: 'หลอด' },
  { value: 'อัน', label: 'อัน' },
  { value: 'กิโลกรัม', label: 'กิโลกรัม' },
  { value: 'แผ่น', label: 'แผ่น' },
  { value: 'ม้วน', label: 'ม้วน' },
  { value: 'กล่อง', label: 'กล่อง' },
  { value: 'ถุง', label: 'ถุง' }
];

const ProjectPriceManagement = () => {
  const { employee } = useAuth();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState(null);
  
  // Customer search state
  const [customerSearchTerm, setCustomerSearchTerm] = useState('');
  
  // Mode selection
  const [priceMode, setPriceMode] = useState(null); // 'project' | 'branch' | 'customer'
  
  // Edit mode
  const [editingProjectId, setEditingProjectId] = useState(null);
  
  // Project Code Mode (auto or manual)
  const [projectCodeMode, setProjectCodeMode] = useState('auto'); // 'auto' | 'manual'
  
  // Form state
  const [formData, setFormData] = useState({
    project_code: '',
    project_name: '',
    customer_code: '',
    customer_name: '',
    branch_code: '',
    site_branch_code: '',  // สาขาของไซต์งาน (สำหรับโหมดสาขา)
    price_start_date: '',
    price_end_date: '',
    request_by: '',
    request_date: new Date().toISOString().split('T')[0],
    remark: '',
  });
  
  const [items, setItems] = useState([]);
  const [branches, setBranches] = useState([]);
  
  // File upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  
  // Employee search state
  const [employeeSearchTerm, setEmployeeSearchTerm] = useState('');
  const [employeeDisplayName, setEmployeeDisplayName] = useState(''); // แสดงชื่อในช่อง input
  const [showEmployeeDropdown, setShowEmployeeDropdown] = useState(false);
  const [filteredEmployees, setFilteredEmployees] = useState([]);
  const employeeDropdownRef = useRef(null);
  
  // Filter selection state
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [filterCriteria, setFilterCriteria] = useState({
    categories: [],
    brands: [],
    groups: [],
    subGroups: [],
    colors: [],
    thicknesses: []
  });
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
  
  // Global price and quantity for all filtered items
  const [globalPrice, setGlobalPrice] = useState('');
  const [globalQuantity, setGlobalQuantity] = useState('');
  const [globalUnit, setGlobalUnit] = useState('');

  useEffect(() => {
    if (employee?.id) {
      loadProjects();
    }
    loadBranches();
    loadProjectCodeMode();
  }, [employee?.id]);

  // Close employee dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (employeeDropdownRef.current && !employeeDropdownRef.current.contains(event.target)) {
        setShowEmployeeDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Filter employees based on search term - ใช้ API search แทน
  useEffect(() => {
    const searchEmployees = async () => {
      if (employeeSearchTerm.trim() === '') {
        setFilteredEmployees([]);
        setShowEmployeeDropdown(false);
        return;
      }

      try {
        const res = await api.get('/api/employees', {
          params: {
            q: employeeSearchTerm.trim(),
            page: 1,
            page_size: 20
          }
        });
        console.log('Search results:', res.data);
        const results = res.data?.data || [];
        setFilteredEmployees(results);
        setShowEmployeeDropdown(results.length > 0);
      } catch (err) {
        console.error('Error searching employees:', err);
        setFilteredEmployees([]);
        setShowEmployeeDropdown(false);
      }
    };

    // Debounce search - รอ 300ms หลังจากพิมพ์เสร็จ
    const timeoutId = setTimeout(() => {
      searchEmployees();
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [employeeSearchTerm]);

  // ⭐ Load filter options when categories change
  useEffect(() => {
    if (filterCriteria.categories.length > 0) {
      loadFilterOptions();
    }
  }, [filterCriteria.categories]);

  // ⭐ Reload matched SKUs when any filter changes
  useEffect(() => {
    if (filterCriteria.categories.length > 0) {
      loadMatchedSkus();
    }
  }, [filterCriteria.brands, filterCriteria.groups, filterCriteria.subGroups, filterCriteria.colors, filterCriteria.thicknesses]);

  // ⭐ Reload filter options when other filters change (to show only available options)
  useEffect(() => {
    if (filterCriteria.categories.length > 0) {
      loadFilterOptions();
    }
  }, [filterCriteria.brands, filterCriteria.groups, filterCriteria.subGroups, filterCriteria.colors, filterCriteria.thicknesses]);

  // ⭐ Product search for individual items
  useEffect(() => {
    if (filterCriteria.categories.length > 0) {
      loadFilterOptions();
    }
  }, [filterCriteria.brands, filterCriteria.groups, filterCriteria.subGroups, filterCriteria.colors, filterCriteria.thicknesses]);

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/api/project-prices/', {
        params: {
          employee_code: employee?.id
        }
      });
      // ข้อมูลจาก backend ถูกกรองแล้ว ไม่ต้องกรองอีก
      setProjects(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error('Error loading projects:', err);
      setError('ไม่สามารถโหลดข้อมูลโครงการได้');
      setProjects([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const loadBranches = async () => {
    try {
      const res = await api.get('/api/branches');
      // API returns {branches: [...]}
      const branchList = res.data?.branches || res.data || [];
      setBranches(Array.isArray(branchList) ? branchList : []);
    } catch (err) {
      console.error('Error loading branches:', err);
      setBranches([]); // Set empty array on error
    }
  };

  const loadProjectCodeMode = async () => {
    try {
      const res = await api.get('/api/config/settings');
      const mode = res.data?.system_config?.project_code_mode || 'auto';
      setProjectCodeMode(mode);
    } catch (err) {
      console.error('Error loading project code mode:', err);
      setProjectCodeMode('auto'); // Default to auto
    }
  };

  // Generate project code based on mode
  const generateProjectCode = () => {
    const now = new Date();
    const buddhistYear = String(now.getFullYear() + 543).slice(-2); // YY (พ.ศ.)
    const month = String(now.getMonth() + 1).padStart(2, '0'); // MM

    if (priceMode === 'project') {
      return `PJ${buddhistYear}${month}`;
    } else if (priceMode === 'branch') {
      const branchCode = (employee?.branchId || 'XX').slice(-2).toUpperCase();
      return `${branchCode}${buddhistYear}${month}`;
    } else if (priceMode === 'customer') {
      const custCode = formData.customer_code || '';
      return `${buddhistYear}${month}${custCode}`;
    }
    return '';
  };

  // Handle mode change
  const handleModeChange = (mode) => {
    setPriceMode(mode);
    setFormData({
      project_code: '',
      project_name: '',
      customer_code: '',
      customer_name: '',
      branch_code: '',
      site_branch_code: '',
      price_start_date: '',
      price_end_date: '',
      request_by: '',
      request_date: new Date().toISOString().split('T')[0],
      remark: '',
    });
    setItems([]);
    setEmployeeSearchTerm('');
    setEmployeeDisplayName('');
  };

  // Fetch customer name from API
  const fetchCustomerName = async (customerCode) => {
    try {
      const res = await api.post(`/api/customer/search?code=${customerCode}`);
      if (res.data && res.data.name) {
        setFormData(prev => ({...prev, customer_name: res.data.name}));
      }
    } catch (err) {
      console.error('Error fetching customer name:', err);
      setFormData(prev => ({...prev, customer_name: ''}));
    }
  };

  // ⭐ Load filter options dynamically based on current filters
  const loadFilterOptions = async () => {
    try {
      const selectedCategories = filterCriteria.categories || [];
      
      if (selectedCategories.length === 0) {
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

      await Promise.all(
        selectedCategories.map(async (cat) => {
          const categoryCode = categoryMap[cat];
          
          if (!categoryCode) return;

          try {
            const url = categoryCode === 'G' 
              ? '/api/items/glass/filter-options'
              : `/api/items/categories/${categoryCode}/filter-options`;
            
            // ⭐ Build filter params - ส่งทุกค่าที่เลือก (ไม่ใช่แค่ค่าแรก)
            const params = {};
            
            // สำหรับกระจก ใช้ 'type' แทน 'group'
            if (categoryCode === 'G') {
              if (filterCriteria.brands?.length > 0) params.brand = filterCriteria.brands.join(',');
              if (filterCriteria.groups?.length > 0) params.type = filterCriteria.groups.join(',');
              if (filterCriteria.subGroups?.length > 0) params.subGroup = filterCriteria.subGroups.join(',');
              if (filterCriteria.colors?.length > 0) params.color = filterCriteria.colors.join(',');
              if (filterCriteria.thicknesses?.length > 0) params.thickness = filterCriteria.thicknesses.join(',');
            } else {
              if (filterCriteria.brands?.length > 0) params.brand = filterCriteria.brands.join(',');
              if (filterCriteria.groups?.length > 0) params.group = filterCriteria.groups.join(',');
              if (filterCriteria.subGroups?.length > 0) params.subGroup = filterCriteria.subGroups.join(',');
              if (filterCriteria.colors?.length > 0) params.color = filterCriteria.colors.join(',');
              if (filterCriteria.thicknesses?.length > 0) params.thickness = filterCriteria.thicknesses.join(',');
            }
            
            const response = await api.get(url, { params });
            const data = response.data;

            // ⭐ Parse filter options from API response
            // Glass endpoint returns: brands, types, subGroups, colors, thicknesses with {value, label}
            // Items endpoint returns: brand, group, subGroup, color, thickness with {code, name}
            
            if (data.brands) {
              data.brands.forEach(b => {
                allOptions.brands.add(JSON.stringify({
                  value: b.value,
                  label: b.label
                }));
              });
            } else if (data.brand) {
              data.brand.forEach(b => {
                allOptions.brands.add(JSON.stringify({
                  value: b.code,
                  label: b.name
                }));
              });
            }
            
            if (data.types) {
              data.types.forEach(g => {
                allOptions.groups.add(JSON.stringify({
                  value: g.value,
                  label: g.label
                }));
              });
            } else if (data.group) {
              data.group.forEach(g => {
                allOptions.groups.add(JSON.stringify({
                  value: g.code,
                  label: g.name
                }));
              });
            }
            
            if (data.subGroups) {
              data.subGroups.forEach(s => {
                allOptions.subGroups.add(JSON.stringify({
                  value: s.value,
                  label: s.label
                }));
              });
            } else if (data.subGroup) {
              data.subGroup.forEach(s => {
                allOptions.subGroups.add(JSON.stringify({
                  value: s.code,
                  label: s.name
                }));
              });
            }
            
            if (data.colors) {
              data.colors.forEach(c => {
                allOptions.colors.add(JSON.stringify({
                  value: c.value,
                  label: c.label
                }));
              });
            } else if (data.color) {
              data.color.forEach(c => {
                allOptions.colors.add(JSON.stringify({
                  value: c.code,
                  label: c.name
                }));
              });
            }
            
            if (data.thicknesses) {
              data.thicknesses.forEach(t => {
                allOptions.thicknesses.add(JSON.stringify({
                  value: t.value,
                  label: t.label
                }));
              });
            } else if (data.thickness) {
              data.thickness.forEach(t => {
                allOptions.thicknesses.add(JSON.stringify({
                  value: t.code,
                  label: t.name
                }));
              });
            }
          } catch (err) {
            console.error(`Error loading filter options for category ${categoryCode}:`, err);
          }
        })
      );

      const finalOptions = {
        categories: CATEGORY_OPTIONS,
        brands: Array.from(allOptions.brands).map(b => JSON.parse(b)).sort((a, b) => a.label.localeCompare(b.label)),
        groups: Array.from(allOptions.groups).map(g => JSON.parse(g)).sort((a, b) => a.label.localeCompare(b.label)),
        subGroups: Array.from(allOptions.subGroups).map(s => JSON.parse(s)).sort((a, b) => a.label.localeCompare(b.label)),
        colors: Array.from(allOptions.colors).map(c => JSON.parse(c)).sort((a, b) => a.label.localeCompare(b.label)),
        thicknesses: Array.from(allOptions.thicknesses).map(t => JSON.parse(t)).sort((a, b) => a.label.localeCompare(b.label))
      };
      
      setFilterOptions(finalOptions);
    } catch (error) {
      console.error('Error loading filter options:', error);
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

  // ⭐ Load matched SKUs with filters sent to backend
  const loadMatchedSkus = async () => {
    try {
      setLoadingSkus(true);
      
      // ⭐ Build filter params to send to backend
      const filterParams = {
        categories: filterCriteria.categories || [],
        brands: filterCriteria.brands || [],
        groups: filterCriteria.groups || [],
        subGroups: filterCriteria.subGroups || [],
        colors: filterCriteria.colors || [],
        thicknesses: filterCriteria.thicknesses || []
      };
      
      const res = await api.post('/api/promotions/get-skus-by-filter', filterParams);
      const skus = res.data?.skus || [];
      setMatchedSkus(skus);
    } catch (err) {
      console.error('Error loading matched SKUs:', err);
      setMatchedSkus([]);
    } finally {
      setLoadingSkus(false);
    }
  };

  // ⭐ Handle filter toggle (for multi-select filters)
  const handleFilterToggle = (field, value) => {
    setFilterCriteria(prev => {
      const current = prev[field] || [];
      const newValues = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [field]: newValues };
    });
  };

  // ⭐ Handle category toggle
  const handleCategoryToggle = (value) => {
    setFilterCriteria(prev => {
      const current = prev.categories || [];
      const newCategories = current.includes(value)
        ? current.filter(c => c !== value)
        : [...current, value];
      return { ...prev, categories: newCategories };
    });
  };

  // ⭐ Clear all filters
  const clearAllFilters = () => {
    setFilterCriteria({
      categories: [],
      brands: [],
      groups: [],
      subGroups: [],
      colors: [],
      thicknesses: []
    });
    setMatchedSkus([]);
  };

  const addItemsFromFilter = () => {
    if (matchedSkus.length === 0) {
      alert('ไม่พบสินค้าที่ตรงกับเงื่อนไข');
      return;
    }

    // ตรวจสอบว่ากรอกราคาแล้ว
    if (!globalPrice || parseFloat(globalPrice) <= 0) {
      alert('กรุณากรอกราคา');
      return;
    }

    // สร้างชื่อสินค้าจาก filter ที่เลือก (ไม่มี code และไม่มี "-")
    const filterSummaryParts = [];
    
    // Category
    if (filterCriteria.categories.length > 0) {
      filterSummaryParts.push(filterCriteria.categories.join(', '));
    }
    
    // Brand
    if (filterCriteria.brands.length > 0) {
      const brandNames = filterCriteria.brands.map(b => {
        const option = filterOptions.brands.find(opt => opt.value === b);
        return option ? extractNameFromLabel(option.label) : b;
      });
      filterSummaryParts.push(brandNames.join(', '));
    }
    
    // Group
    if (filterCriteria.groups.length > 0) {
      const groupNames = filterCriteria.groups.map(g => {
        const option = filterOptions.groups.find(opt => opt.value === g);
        return option ? extractNameFromLabel(option.label) : g;
      });
      filterSummaryParts.push(groupNames.join(', '));
    }
    
    // SubGroup
    if (filterCriteria.subGroups.length > 0) {
      const subGroupNames = filterCriteria.subGroups.map(s => {
        const option = filterOptions.subGroups.find(opt => opt.value === s);
        return option ? extractNameFromLabel(option.label) : s;
      });
      filterSummaryParts.push(subGroupNames.join(', '));
    }
    
    // Color
    if (filterCriteria.colors.length > 0) {
      const colorNames = filterCriteria.colors.map(c => {
        const option = filterOptions.colors.find(opt => opt.value === c);
        return option ? extractNameFromLabel(option.label) : c;
      });
      filterSummaryParts.push(colorNames.join(', '));
    }
    
    // Thickness
    if (filterCriteria.thicknesses.length > 0) {
      const thicknessNames = filterCriteria.thicknesses.map(t => {
        const option = filterOptions.thicknesses.find(opt => opt.value === t);
        return option ? extractNameFromLabel(option.label) : t;
      });
      filterSummaryParts.push(thicknessNames.join(', '));
    }
    
    const productName = filterSummaryParts.join(' ');
    
    // เพิ่มเป็นแถวเดียวที่สรุป filter ทั้งหมด (แต่เก็บ SKU list ไว้สำหรับบันทึก)
    const newItem = {
      product_name: productName,
      unit: globalUnit || '',
      price: globalPrice,
      quantity: globalQuantity || '',
      // ⭐ เก็บ SKU list ไว้สำหรับบันทึกลง database (ไม่แสดงบนหน้าจอ)
      skus: matchedSkus.map(sku => ({
        sku: sku.sku,
        product_name: sku.description || '',
        brand: sku.brand || '',
        thickness: sku.thickness || ''
      }))
    };

    setItems([...items, newItem]);
    setShowFilterModal(false);
    
    // Reset filter and global values
    setFilterCriteria({
      categories: [],
      brands: [],
      groups: [],
      subGroups: [],
      colors: [],
      thicknesses: []
    });
    setMatchedSkus([]);
    setGlobalPrice('');
    setGlobalQuantity('');
    setGlobalUnit('');
    setOpenDropdown({});
    
    alert(`เพิ่มรายการสินค้า (${matchedSkus.length} SKUs) เรียบร้อยแล้ว`);
  };

  // ⭐ อัปโหลดไฟล์โครงการ (เก็บที่ folder ตามรหัสโครงการ)
  const handleFileUpload = async (projectCode) => {
    if (!selectedFile) return;

    try {
      setUploadingFile(true);
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await api.post(`/api/project-files/upload/${projectCode}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      console.log('✅ File uploaded successfully');
      console.log('📁 File path:', response.data?.file_path);
      console.log('📊 Response:', response.data);
      
      // แสดง success message พร้อม path
      if (response.data?.file_path) {
        alert(`✅ ไฟล์อัพโหลดสำเร็จ\n📁 บันทึกไปที่: ${response.data.file_path}`);
      }
      
      setSelectedFile(null);
    } catch (err) {
      console.error('❌ Error uploading file:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'เกิดข้อผิดพลาดในการอัพโหลด';
      alert(`❌ ข้อผิดพลาด: ${errorMsg}`);
    } finally {
      setUploadingFile(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // ⭐ Validate project_code ในโหมด manual
    if (projectCodeMode === 'manual' && !editingProjectId) {
      if (!formData.project_code || formData.project_code.trim() === '') {
        alert('กรุณากรอกรหัสโครงการ');
        return;
      }
    }
    
    // ⭐ ไม่บังคับให้ใส่สินค้า แต่ต้องใส่ชื่อโครงการ
    // items.length === 0 ไม่ต้องแจ้งเตือน

    // Validate วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา
    if (formData.price_end_date && formData.price_start_date) {
      if (formData.price_end_date <= formData.price_start_date) {
        alert('วันที่สิ้นสุดต้องมากกว่าวันที่เริ่มใช้ราคา');
        return;
      }
    }

    try {
      // ⭐ แยก items ที่มี skus array ออกเป็นแต่ละ SKU
      const expandedItems = [];
      items.forEach(item => {
        if (item.skus && item.skus.length > 0) {
          // ถ้ามี skus array แปลว่าเป็น item จาก filter - แยกเป็นแต่ละ SKU
          // ⭐ ใช้ชื่อสินค้าจาก filter (item.product_name) แทน description ของแต่ละ SKU
          item.skus.forEach(skuData => {
            expandedItems.push({
              sku: skuData.sku,
              product_name: item.product_name, // ⭐ ใช้ชื่อจาก filter ไม่ใช่ skuData.product_name
              brand: skuData.brand,
              thickness: skuData.thickness,
              unit: item.unit,
              price: item.price,
              quantity: item.quantity
            });
          });
        } else {
          // ถ้าไม่มี skus array แปลว่าเป็น item ที่เพิ่มทีละรายการ
          expandedItems.push({
            sku: item.sku || '',
            product_name: item.product_name,
            brand: item.brand || '',
            thickness: item.thickness || '',
            unit: item.unit,
            price: item.price,
            quantity: item.quantity
          });
        }
      });
      
      const payload = {
        ...formData,
        // ✅ ส่ง project_name เสมอ (สำหรับโหมด customer คือ ชื่อแคมเปญ)
        project_name: formData.project_name,
        // ✅ เพิ่ม employee code
        created_by_employee_code: employee?.id,
        // ⭐ เพิ่ม price_mode flag
        price_mode: priceMode,
        items: expandedItems
      };

      if (editingProjectId) {
        // Update existing project
        const response = await api.put(`/api/project-prices/${editingProjectId}`, payload);
        const projectCode = response.data?.project_code || formData.project_code;
        
        // ⭐ อัปโหลดไฟล์ถ้ามี (เก็บที่ folder ตามรหัสโครงการ)
        if (selectedFile && projectCode) {
          await handleFileUpload(projectCode);
        }
        
        alert('อัพเดทราคาโครงการเรียบร้อยแล้ว');
        setEditingProjectId(null);
      } else {
        // Create new project - เลขที่จะถูกสร้างโดย backend
        const response = await api.post('/api/project-prices/', payload);
        const generatedCode = response.data?.project_code || 'สร้างสำเร็จ';
        
        // ⭐ อัปโหลดไฟล์ถ้ามี (เก็บที่ folder ตามรหัสโครงการ)
        if (selectedFile && generatedCode && generatedCode !== 'สร้างสำเร็จ') {
          await handleFileUpload(generatedCode);
        }
        
        alert(`บันทึกราคาโครงการเรียบร้อยแล้ว\nเลขที่ใบคำขอ: ${generatedCode}`);
      }
      
      // Reset form
      setFormData({
        project_code: '',
        project_name: '',
        customer_code: '',
        customer_name: '',
        branch_code: '',
        site_branch_code: '',
        price_start_date: '',
        price_end_date: '',
        request_by: '',
        request_date: new Date().toISOString().split('T')[0],
        remark: '',
      });
      setItems([]);
      setPriceMode(null);
      setShowForm(false);
      setEmployeeSearchTerm('');
      setEmployeeDisplayName('');
      loadProjects();
    } catch (err) {
      console.error('Error saving project:', err);
      const errorMsg = err.response?.data?.detail || 'เกิดข้อผิดพลาดในการบันทึก';
      alert(errorMsg);
    }
  };

  const addItem = () => {
    setItems([...items, {
      product_name: '',
      unit: '',
      price: '',
      quantity: '',
    }]);
  };

  const removeItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index][field] = value;
    setItems(newItems);
  };

  // ⭐ Remove SKU from matched list
  const removeMatchedSku = (skuToRemove) => {
    setMatchedSkus(prev => prev.filter(item => item.sku !== skuToRemove));
  };

  const deleteProject = async (projectId) => {
    if (!confirm('ต้องการยกเลิกราคาโครงการนี้หรือไม่?')) return;
    
    try {
      // ⭐ เปลี่ยนสถานะเป็น "canceled" แทนการลบ
      await api.put(`/api/project-prices/${projectId}/status`, null, {
        params: { status: 'canceled' }
      });
      alert('ยกเลิกราคาโครงการเรียบร้อยแล้ว');
      loadProjects();
    } catch (err) {
      console.error('Error canceling project:', err);
      alert('เกิดข้อผิดพลาดในการยกเลิก');
    }
  };

  const updateStatus = async (projectId, status) => {
    try {
      await api.put(`/api/project-prices/${projectId}/status`, null, {
        params: { status }
      });
      loadProjects();
    } catch (err) {
      console.error('Error updating status:', err);
    }
  };

  // Check if project is within date range
  const isProjectActive = (project) => {
    const today = new Date().toISOString().split('T')[0];
    
    // ⭐ ถ้าเลยวันสิ้นสุด ให้อัปเดตสถานะเป็น "expired" อัตโนมัติ
    if (project.status !== 'canceled' && today > project.price_end_date) {
      if (project.status !== 'expired') {
        updateStatus(project.project_id, 'expired');
      }
      return false;
    }
    
    return project.price_start_date <= today && today <= project.price_end_date;
  };

  // Start editing project
  // ⭐ Helper function: แยกชื่อจาก label (เอาส่วนหลัง " - ")
  const extractNameFromLabel = (label) => {
    if (!label) return '';
    const parts = label.split(' - ');
    return parts.length > 1 ? parts[1] : label;
  };

  // ⭐ Helper function: แปลง SKU เป็นชื่อสินค้า (ใช้ filterOptions ที่ส่งเข้ามา)
  const getProductNameFromSku = (sku, options = filterOptions) => {
    if (!sku) return '';
    
    const categoryMap = {
      'G': 'Glass',
      'A': 'Aluminum',
      'S': 'Sealant',
      'Y': 'Gypsum',
      'C': 'C-Line',
      'E': 'Accessories'
    };
    
    const parts = [];
    const categoryCode = sku[0];
    
    // ตัวอักษรแรก = Category
    const category = categoryMap[categoryCode] || categoryCode;
    parts.push(category);
    
    // ⭐ SKU Structure:
    // Glass (G): G + Brand(2) + Type(2) + SubGroup(3) + Color(2) + Thickness(2) + Width(3) + Length(3) = 18 chars
    // Others: X + Brand(2) + Group(2) + SubGroup(3) + Color(2) + Thickness(2) = 12 chars
    // เราจะดูแค่ 12 ตัวแรก (ไม่รวม Width/Length ของกระจก)
    
    const skuCore = sku.substring(0, Math.min(12, sku.length));
    
    // ตำแหน่ง 2-3: Brand
    if (skuCore.length >= 3) {
      const brandCode = skuCore.substring(1, 3);
      const brandOption = options.brands?.find(b => b.value === brandCode);
      if (brandOption) {
        parts.push(extractNameFromLabel(brandOption.label));
      }
    }
    
    // ตำแหน่ง 4-5: Group/Type
    let groupCode = null;
    if (skuCore.length >= 5) {
      groupCode = skuCore.substring(3, 5);
      const groupOption = options.groups?.find(g => g.value === groupCode);
      if (groupOption) {
        parts.push(extractNameFromLabel(groupOption.label));
      }
    }
    
    // ตำแหน่ง 6-8: SubGroup (สำหรับกระจก ต้องหา SubGroup ที่ตรงกับ Group)
    if (skuCore.length >= 8) {
      const subGroupCode = skuCore.substring(5, 8);
      
      // ⭐ สำหรับกระจก ต้องหา SubGroup ที่มี groupCode ตรงกัน
      let subGroupOption;
      if (categoryCode === 'G' && groupCode) {
        subGroupOption = options.subGroups?.find(s => 
          s.value === subGroupCode && s.groupCode === groupCode
        );
      } else {
        subGroupOption = options.subGroups?.find(s => s.value === subGroupCode);
      }
      
      if (subGroupOption) {
        parts.push(extractNameFromLabel(subGroupOption.label));
      }
    }
    
    // ตำแหน่ง 9-10: Color
    if (skuCore.length >= 10) {
      const colorCode = skuCore.substring(8, 10);
      const colorOption = options.colors?.find(c => c.value === colorCode);
      if (colorOption) {
        parts.push(extractNameFromLabel(colorOption.label));
      }
    }
    
    // ตำแหน่ง 11-12: Thickness
    if (skuCore.length >= 12) {
      const thicknessCode = skuCore.substring(10, 12);
      const thicknessOption = options.thicknesses?.find(t => t.value === thicknessCode);
      if (thicknessOption) {
        parts.push(extractNameFromLabel(thicknessOption.label));
      }
    }
    
    return parts.join(' ');
  };

  const startEditProject = async (project) => {
    setEditingProjectId(project.project_id);
    
    // ⭐ แปลงรูปแบบวันที่จาก "2026-04-24 00:00:00" เป็น "2026-04-24"
    const formatDateForInput = (dateStr) => {
      if (!dateStr) return '';
      return dateStr.split(' ')[0]; // ตัดเวลาออก
    };
    
    setFormData({
      project_code: project.project_code,
      project_name: project.project_name || '',
      customer_code: project.customer_code || '',
      customer_name: project.customer_name || '',
      branch_code: project.branch_code || '',
      site_branch_code: project.site_branch_code || '',
      price_start_date: formatDateForInput(project.price_start_date),
      price_end_date: formatDateForInput(project.price_end_date),
      request_by: project.request_by || '',
      request_date: formatDateForInput(project.request_date) || new Date().toISOString().split('T')[0],
      remark: project.remark || '',
    });
    
    // ⭐ ถ้ามีรหัสพนักงาน ให้ดึงชื่อมาแสดง
    if (project.request_by) {
      setEmployeeSearchTerm(project.request_by);
      // ดึงชื่อพนักงานจาก API
      try {
        const res = await api.get(`/api/employees/${project.request_by}`);
        if (res.data && res.data.name) {
          setEmployeeDisplayName(res.data.name);
        } else {
          setEmployeeDisplayName(project.request_by);
        }
      } catch (err) {
        console.error('Error fetching employee name:', err);
        setEmployeeDisplayName(project.request_by);
      }
    } else {
      setEmployeeSearchTerm('');
      setEmployeeDisplayName('');
    }
    
    // ⭐ ดึง categories จาก items เพื่อโหลด filterOptions
    const categories = new Set();
    (project.items || []).forEach(item => {
      if (item.sku && item.sku.length > 0) {
        const categoryCode = item.sku[0];
        const categoryMap = {
          'G': 'Glass',
          'A': 'Aluminum',
          'S': 'Sealant',
          'Y': 'Gypsum',
          'C': 'C-Line',
          'E': 'Accessories'
        };
        if (categoryMap[categoryCode]) {
          categories.add(categoryMap[categoryCode]);
        }
      }
    });
    
    // ⭐ โหลด filterOptions สำหรับ categories ที่พบ (แยกตามประเภท)
    const filterOptionsByCategory = {};
    if (categories.size > 0) {
      try {
        const categoryMap = {
          'Glass': 'G',
          'Aluminum': 'A',
          'Sealant': 'S',
          'Gypsum': 'Y',
          'C-Line': 'C',
          'Accessories': 'E'
        };

        await Promise.all(
          Array.from(categories).map(async (cat) => {
            const categoryCode = categoryMap[cat];
            if (!categoryCode) return;

            try {
              // ⭐ สำหรับกระจก ต้องดึง SubGroup ตาม Group ที่มีใน SKU
              if (categoryCode === 'G') {
                // หา Group codes ทั้งหมดที่มีในกระจก
                const glassGroupCodes = new Set();
                (project.items || []).forEach(item => {
                  if (item.sku && item.sku[0] === 'G' && item.sku.length >= 5) {
                    glassGroupCodes.add(item.sku.substring(3, 5));
                  }
                });

                filterOptionsByCategory[cat] = {
                  brands: [],
                  groups: [],
                  subGroups: [],
                  colors: [],
                  thicknesses: []
                };

                // ดึง options พื้นฐาน (ไม่มี filter)
                const baseResponse = await api.get('/api/items/glass/filter-options');
                const baseData = baseResponse.data;

                if (baseData.brands) {
                  filterOptionsByCategory[cat].brands = baseData.brands.map(b => ({
                    value: b.value,
                    label: b.label
                  }));
                }

                if (baseData.types) {
                  filterOptionsByCategory[cat].groups = baseData.types.map(g => ({
                    value: g.value,
                    label: g.label
                  }));
                }

                if (baseData.colors) {
                  filterOptionsByCategory[cat].colors = baseData.colors.map(c => ({
                    value: c.value,
                    label: c.label
                  }));
                }

                if (baseData.thicknesses) {
                  filterOptionsByCategory[cat].thicknesses = baseData.thicknesses.map(t => ({
                    value: t.value,
                    label: t.label
                  }));
                }

                // ⭐ ดึง SubGroup แยกตาม Group
                for (const groupCode of glassGroupCodes) {
                  try {
                    const subGroupResponse = await api.get('/api/items/glass/filter-options', {
                      params: { type: groupCode }
                    });
                    if (subGroupResponse.data.subGroups) {
                      subGroupResponse.data.subGroups.forEach(s => {
                        // เก็บ SubGroup พร้อม Group code เพื่อใช้ในการ match
                        filterOptionsByCategory[cat].subGroups.push({
                          value: s.value,
                          label: s.label,
                          groupCode: groupCode
                        });
                      });
                    }
                  } catch (err) {
                    console.error(`Error loading subgroups for glass group ${groupCode}:`, err);
                  }
                }
              } else {
                // สำหรับประเภทอื่นๆ ดึงแบบปกติ
                const url = `/api/items/categories/${categoryCode}/filter-options`;
                const response = await api.get(url);
                const data = response.data;

                filterOptionsByCategory[cat] = {
                  brands: [],
                  groups: [],
                  subGroups: [],
                  colors: [],
                  thicknesses: []
                };

                if (data.brand) {
                  filterOptionsByCategory[cat].brands = data.brand.map(b => ({
                    value: b.code,
                    label: b.name
                  }));
                }

                if (data.group) {
                  filterOptionsByCategory[cat].groups = data.group.map(g => ({
                    value: g.code,
                    label: g.name
                  }));
                }

                if (data.subGroup) {
                  filterOptionsByCategory[cat].subGroups = data.subGroup.map(s => ({
                    value: s.code,
                    label: s.name
                  }));
                }

                if (data.color) {
                  filterOptionsByCategory[cat].colors = data.color.map(c => ({
                    value: c.code,
                    label: c.name
                  }));
                }

                if (data.thickness) {
                  filterOptionsByCategory[cat].thicknesses = data.thickness.map(t => ({
                    value: t.code,
                    label: t.name
                  }));
                }
              }
            } catch (err) {
              console.error(`Error loading filter options for category ${categoryCode}:`, err);
            }
          })
        );

        // รวม options ทั้งหมดเพื่อ set state (สำหรับใช้ใน filter modal)
        const allOptions = {
          brands: new Set(),
          groups: new Set(),
          subGroups: new Set(),
          colors: new Set(),
          thicknesses: new Set()
        };

        Object.values(filterOptionsByCategory).forEach(opts => {
          opts.brands.forEach(b => allOptions.brands.add(JSON.stringify({ value: b.value, label: b.label })));
          opts.groups.forEach(g => allOptions.groups.add(JSON.stringify({ value: g.value, label: g.label })));
          opts.subGroups.forEach(s => allOptions.subGroups.add(JSON.stringify({ value: s.value, label: s.label })));
          opts.colors.forEach(c => allOptions.colors.add(JSON.stringify({ value: c.value, label: c.label })));
          opts.thicknesses.forEach(t => allOptions.thicknesses.add(JSON.stringify({ value: t.value, label: t.label })));
        });

        tempFilterOptions = {
          categories: CATEGORY_OPTIONS,
          brands: Array.from(allOptions.brands).map(b => JSON.parse(b)).sort((a, b) => a.label.localeCompare(b.label)),
          groups: Array.from(allOptions.groups).map(g => JSON.parse(g)).sort((a, b) => a.label.localeCompare(b.label)),
          subGroups: Array.from(allOptions.subGroups).map(s => JSON.parse(s)).sort((a, b) => a.label.localeCompare(b.label)),
          colors: Array.from(allOptions.colors).map(c => JSON.parse(c)).sort((a, b) => a.label.localeCompare(b.label)),
          thicknesses: Array.from(allOptions.thicknesses).map(t => JSON.parse(t)).sort((a, b) => a.label.localeCompare(b.label))
        };
        
        setFilterOptions(tempFilterOptions);
      } catch (error) {
        console.error('Error loading filter options for edit:', error);
      }
    }
    
    // ⭐ รวมกลุ่ม SKU ที่มีราคา, หน่วย, จำนวนเหมือนกัน
    const groupedItems = [];
    const itemGroups = {};
    
    (project.items || []).forEach(item => {
      // สร้าง key สำหรับจัดกลุ่ม (ราคา + หน่วย + จำนวน + ประเภท)
      const groupKey = `${item.price}_${item.unit}_${item.quantity || ''}_${item.sku?.[0] || ''}`;
      
      if (!itemGroups[groupKey]) {
        itemGroups[groupKey] = {
          product_name: item.product_name || '',
          unit: item.unit,
          price: item.price,
          quantity: item.quantity,
          skus: []
        };
      }
      
      // เพิ่ม SKU เข้ากลุ่ม
      itemGroups[groupKey].skus.push({
        sku: item.sku,
        product_name: item.product_name,
        brand: item.brand,
        thickness: item.thickness
      });
    });
    
    // แปลงเป็น array และสร้างชื่อสินค้าจากกลุ่ม
    Object.values(itemGroups).forEach(group => {
      if (group.skus.length > 1) {
        // ⭐ ดูที่ SKU - หาตำแหน่งที่ตรงกันทั้งหมด
        const skus = group.skus.map(s => s.sku);
        
        // หาความยาวของ SKU ที่ตรงกัน (ดูแค่ 12 ตัวแรก)
        let commonSkuLength = 0;
        if (skus.length > 0) {
          const firstSku = skus[0].substring(0, 12);
          for (let i = 0; i < firstSku.length; i++) {
            // ตรวจสอบว่าตำแหน่ง i ตรงกันทั้งหมด
            if (skus.every(sku => sku.substring(0, 12)[i] === firstSku[i])) {
              commonSkuLength = i + 1;
            } else {
              break;
            }
          }
        }
        
        // ถ้ามีส่วนที่ตรงกัน ให้สร้างชื่อจาก common SKU
        if (commonSkuLength > 0) {
          const commonSku = skus[0].substring(0, commonSkuLength);
          
          // ⭐ หาประเภทของ SKU และใช้ options ที่ถูกต้อง
          const categoryCode = commonSku[0];
          const categoryMap = {
            'G': 'Glass',
            'A': 'Aluminum',
            'S': 'Sealant',
            'Y': 'Gypsum',
            'C': 'C-Line',
            'E': 'Accessories'
          };
          const categoryName = categoryMap[categoryCode];
          const categoryOptions = filterOptionsByCategory[categoryName] || tempFilterOptions;
          
          group.product_name = `${getProductNameFromSku(commonSku, categoryOptions)} (${group.skus.length} SKUs)`;
        } else {
          group.product_name = `${group.skus.length} SKUs`;
        }
      } else {
        // ถ้ามี SKU เดียว ไม่ต้องมี skus array
        const singleSku = group.skus[0];
        group.product_name = singleSku.product_name;
        // ไม่เก็บ skus array ถ้ามีแค่ตัวเดียว (เพื่อให้แก้ไขได้ปกติ)
        delete group.skus;
      }
      groupedItems.push(group);
    });
    
    setItems(groupedItems);
    
    // ⭐ ตั้งค่า priceMode จาก project.price_mode (ถ้าไม่มีให้ดูจาก customer_code)
    const mode = project.price_mode || (project.customer_code ? 'project' : 'branch');
    setPriceMode(mode);
    
    setShowForm(true);
  };

  // ⭐ Filter projects by customer search term และซ่อน canceled
  const filteredProjects = projects.filter(project => {
    // ⭐ ซ่อนรายการที่เป็น canceled
    if (project.status === 'canceled') return false;
    
    if (!customerSearchTerm.trim()) return true;
    
    const searchLower = customerSearchTerm.toLowerCase();
    const customerCode = (project.customer_code || '').toLowerCase();
    const customerName = (project.customer_name || '').toLowerCase();
    const projectCode = (project.project_code || '').toLowerCase();
    const projectName = (project.project_name || '').toLowerCase();
    
    return customerCode.includes(searchLower) || 
           customerName.includes(searchLower) ||
           projectCode.includes(searchLower) ||
           projectName.includes(searchLower);
  });

  return (
    <div className="container mx-auto p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-800">สร้างหมายเลขโครงการ</h1>
        <button
          onClick={() => {
            setPriceMode(null);
            setShowForm(!showForm);
          }}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-5 h-5" />
          เพิ่มรหัสโครงการ
        </button>
      
      </div>
      <div className='font-semibold text-red-600 mb-2 text-xl'>รายละเอียดต้องถูกอนุมัติมาจาก "ใบขอราคาพิเศษ" แล้วเท่านั้น</div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">เพิ่มรหัสโครงการใหม่</h2>
          
          {/* Mode Selection */}
          {!priceMode && !editingProjectId ? (
            <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm font-medium text-gray-700 mb-3">เลือกประเภทโครงการ:</p>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => handleModeChange('project')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition"
                >
                  <div className="font-semibold text-gray-800 hover:text-lg">โครงการ</div>
                  <div className="text-xs text-gray-500 mt-1">รหัสโครงการ (พนักงานขาย Project)</div>
                </button>
                
                <button
                  type="button"
                  onClick={() => handleModeChange('branch')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition"
                >
                  <div className="font-semibold text-gray-800 hover:text-lg">สาขา</div>
                  <div className="text-xs text-gray-500 mt-1">รหัสโครงการของสาขา</div>
                </button>
                
                <button
                  type="button"
                  onClick={() => handleModeChange('customer')}
                  className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-100 transition"
                >
                  <div className="font-semibold text-gray-800 hover:text-lg">ลูกค้าพิเศษ</div>
                  <div className="text-xs text-gray-500 mt-1">ราคาพิเศษ/ลูกค้า</div>
                </button>
              </div>
            </div>
          ) : (
            <div className="mb-4 flex items-center gap-2">
              {!editingProjectId && (
                <>
                  <button
                    type="button"
                    onClick={() => setPriceMode(null)}
                    className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
                  >
                    ← เปลี่ยนประเภท
                  </button>
                  <span className="text-sm font-medium text-gray-600">
                    {priceMode === 'project' && 'โหมด: โครงการ (PJYYMMXXX)'}
                    {priceMode === 'branch' && 'โหมด: สาขา (BRYYMMXXX)'}
                    {priceMode === 'customer' && 'โหมด: ลูกค้าพิเศษ (YYMMCUSTCODE)'}
                  </span>
                </>
              )}
              {editingProjectId && (
                <span className="text-sm font-medium text-blue-600">
                  🔧 กำลังแก้ไขโครงการ
                </span>
              )}
            </div>
          )}
          
          {(priceMode || editingProjectId) && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Row 1: Project Code & Name */}
            {editingProjectId ? (
              // ⭐ โหมดแก้ไข - แสดงฟอร์มตาม priceMode
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      รหัสโครงการ
                    </label>
                    <input
                      type="text"
                      value={formData.project_code}
                      disabled
                      className="w-full border rounded-lg px-3 py-2 bg-gray-100 text-gray-600 cursor-not-allowed"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {priceMode === 'customer' ? 'ชื่อแคมเปญ' : 'ชื่อโครงการ'} <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.project_name}
                      onChange={(e) => setFormData({...formData, project_name: e.target.value})}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder={priceMode === 'customer' ? 'เช่น EFC' : 'เช่น โครงการคอนโดXXX'}
                    />
                  </div>
                </div>
                
                {/* ⭐ แสดงช่องรหัสลูกค้า, ชื่อลูกค้า, และสาขา */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      รหัสลูกค้า {priceMode === 'customer' && <span className="text-red-500">*</span>}
                    </label>
                    <input
                      type="text"
                      required={priceMode === 'customer'}
                      value={formData.customer_code}
                      onChange={(e) => {
                        const code = e.target.value.toUpperCase();
                        setFormData({...formData, customer_code: code});
                        
                        if (code.trim().length > 0) {
                          fetchCustomerName(code.trim());
                        } else {
                          setFormData(prev => ({...prev, customer_name: ''}));
                        }
                      }}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="เช่น 08015AY"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ชื่อลูกค้า
                    </label>
                    <input
                      type="text"
                      value={formData.customer_name}
                      readOnly
                      className="w-full border rounded-lg px-3 py-2 bg-gray-50 text-gray-700"
                      placeholder="ชื่อลูกค้า (อัตโนมัติ)"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      สาขา 
                    </label>
                    <select
                      value={formData.branch_code}
                      onChange={(e) => setFormData({...formData, branch_code: e.target.value})}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">เลือกสาขา</option>
                      {Array.isArray(branches) && branches.map(b => (
                        <option key={b.Code} value={b.Code}>{b.Name} ({b.Code})</option>
                      ))}
                    </select>
                  </div>
                </div>
              </>
            ) : priceMode === 'customer' ? (
              // ฟอร์มสำหรับโหมดลูกค้าพิเศษ - มีชื่อแคมเปญแทนชื่อโครงการ
              <div className="grid grid-cols-3 gap-4">
                {/* Project Code Input (Manual Mode Only) */}
                {projectCodeMode === 'manual' && (
                  <div className="col-span-3">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      รหัสโครงการ <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.project_code}
                      onChange={(e) => setFormData({...formData, project_code: e.target.value.toUpperCase()})}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="กรอกรหัสโครงการ"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      💡 กรอกรหัสโครงการเอง (ระบบไม่สร้างอัตโนมัติ)
                    </p>
                  </div>
                )}
                
                <div className="col-span-3">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ชื่อแคมเปญ <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.project_name}
                    onChange={(e) => setFormData({...formData, project_name: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="เช่น EFC"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    รหัสลูกค้า <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.customer_code}
                    onChange={(e) => {
                      const code = e.target.value.toUpperCase();
                      setFormData({...formData, customer_code: code});
                      
                      if (code.trim().length > 0) {
                        fetchCustomerName(code.trim());
                      } else {
                        setFormData(prev => ({...prev, customer_name: ''}));
                      }
                    }}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="เช่น 08015AY"
                  />
                  {projectCodeMode === 'auto' && (
                    <p className="text-xs text-gray-500 mt-1">
                      💡 รหัสโครงการจะถูกสร้างอัตโนมัติเมื่อบันทึก
                    </p>
                  )}
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ชื่อลูกค้า
                  </label>
                  <input
                    type="text"
                    value={formData.customer_name}
                    readOnly
                    className="w-full border rounded-lg px-3 py-2 bg-gray-50 text-gray-700"
                    placeholder="ชื่อลูกค้า (อัตโนมัติ)"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    สาขา 
                  </label>
                  <select
                    value={formData.branch_code}
                    onChange={(e) => setFormData({...formData, branch_code: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2"
                  >
                    <option value="">เลือกสาขา</option>
                    {Array.isArray(branches) && branches.map(b => (
                      <option key={b.Code} value={b.Code}>{b.Name} ({b.Code})</option>
                    ))}
                  </select>
                </div>
              </div>
            ) : (
              // ฟอร์มสำหรับโหมดโครงการ/สาขา - มีชื่อโครงการ
              <>
                {/* Project Code Input (Manual Mode Only) */}
                {projectCodeMode === 'manual' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      รหัสโครงการ <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      value={formData.project_code}
                      onChange={(e) => setFormData({...formData, project_code: e.target.value.toUpperCase()})}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="กรอกรหัสโครงการ เช่น PJ6704001"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      💡 กรอกรหัสโครงการเอง (ระบบไม่สร้างอัตโนมัติ)
                    </p>
                  </div>
                )}
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    ชื่อโครงการ <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.project_name}
                    onChange={(e) => setFormData({...formData, project_name: e.target.value})}
                    className="w-full border rounded-lg px-3 py-2"
                    placeholder="เช่น โครงการคอนโดXXX"
                  />
                  {projectCodeMode === 'auto' && (
                    <p className="text-xs text-gray-500 mt-1">
                      💡 รหัสโครงการจะถูกสร้างอัตโนมัติเมื่อบันทึก
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      รหัสลูกค้า
                    </label>
                    <input
                      type="text"
                      value={formData.customer_code}
                      onChange={(e) => {
                        const code = e.target.value.toUpperCase();
                        setFormData({...formData, customer_code: code});
                        
                        if (code.trim().length > 0) {
                          fetchCustomerName(code.trim());
                        } else {
                          setFormData(prev => ({...prev, customer_name: ''}));
                        }
                      }}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="เช่น 08015AY"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      ชื่อลูกค้า
                    </label>
                    <input
                      type="text"
                      value={formData.customer_name}
                      readOnly
                      className="w-full border rounded-lg px-3 py-2 bg-gray-50 text-gray-700"
                      placeholder="ชื่อลูกค้า (อัตโนมัติ)"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      สาขา 
                    </label>
                    <select
                      value={formData.branch_code}
                      onChange={(e) => setFormData({...formData, branch_code: e.target.value})}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">เลือกสาขา</option>
                      {Array.isArray(branches) && branches.map(b => (
                        <option key={b.Code} value={b.Code}>{b.Name} ({b.Code})</option>
                      ))}
                    </select>
                  </div>
                </div>
              </>
            )}

            {/* Row 3: Start & End Dates */}
            <div className="grid grid-cols-2 gap-4">           
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  วันที่เริ่มใช้ราคา 
                </label>
                <input
                  type="date"
                  value={formData.price_start_date}
                  onChange={(e) => setFormData({...formData, price_start_date: e.target.value})}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  วันที่สิ้นสุด 
                </label>
                <input
                  type="date"
                  value={formData.price_end_date}
                  onChange={(e) => setFormData({...formData, price_end_date: e.target.value})}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>
            </div>

            {/* Row 4: Approval Date, Attachment & Request By */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  วันที่อนุมัติ
                </label>
                <input
                  type="date"
                  value={formData.request_date}
                  onChange={(e) => setFormData({...formData, request_date: e.target.value})}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  แนบไฟล์โครงการ
                </label>
                <input
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      setSelectedFile(file);
                      console.log('📁 File selected:', file.name, `(${(file.size / 1024).toFixed(2)} KB)`);
                    }
                  }}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                />
                {selectedFile && (
                  <p className="text-sm text-green-600 mt-1">
                    ✅ เลือกไฟล์: {selectedFile.name}
                  </p>
                )}
              </div>

              <div className="relative" ref={employeeDropdownRef}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  ผู้ขอ (รหัสพนักงาน)
                </label>
                <input
                  type="text"
                  value={employeeDisplayName}
                  onChange={(e) => {
                    const value = e.target.value;
                    setEmployeeDisplayName(value);
                    setEmployeeSearchTerm(value);
                    setFormData({...formData, request_by: ''}); // Clear request_by เมื่อพิมพ์ใหม่
                  }}
                  onFocus={() => {
                    if (filteredEmployees.length > 0) {
                      setShowEmployeeDropdown(true);
                    }
                  }}
                  className="w-full border rounded-lg px-3 py-2"
                  placeholder="ค้นหารหัสหรือชื่อพนักงาน"
                />
                
                {showEmployeeDropdown && filteredEmployees.length > 0 && (
                  <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                    {filteredEmployees.map((emp) => (
                      <div
                        key={emp.id}
                        onClick={() => {
                          setEmployeeDisplayName(emp.name); // แสดงชื่อ
                          setEmployeeSearchTerm(emp.name); // ใช้ชื่อสำหรับ search
                          setFormData({...formData, request_by: emp.id}); // เก็บรหัสใน formData
                          setShowEmployeeDropdown(false);
                        }}
                        className="px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0"
                      >
                        <div className="font-medium text-sm">{emp.id}</div>
                        <div className="text-xs text-gray-600">{emp.name}</div>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Debug info */}
                {employeeSearchTerm && filteredEmployees.length === 0 && (
                  <div className="text-xs text-red-500 mt-1">
                    ไม่พบพนักงาน
                  </div>
                )}
              </div>
            </div>

            {/* Row 5: Remark */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                หมายเหตุ
              </label>
              <input
                type="text"
                value={formData.remark}
                onChange={(e) => setFormData({...formData, remark: e.target.value})}
                className="w-full border rounded-lg px-3 py-2"
                placeholder="กรอกรายละเอียดรายการสินค้า เช่น กระจกใส AGC 6 มม."
              />
            </div>

            {/* Items Section */}
            <div className="border-t pt-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold">รายการสินค้า</h3>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowFilterModal(true)}
                    className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                  >
                    <Filter className="w-4 h-4" />
                    เลือกตาม Filter
                  </button>
                </div>
              </div>

              {/* แสดงรายการที่เพิ่มแล้ว */}
              {items.length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-semibold mb-2">รายการที่เพิ่มแล้ว ({items.length})</h4>
                  <div className="border border-gray-200 rounded-lg">
                    <div className="space-y-2 p-2 max-h-96 overflow-y-auto">
                      {items.map((item, index) => (
                        <div key={index} className="bg-gray-50 p-2 rounded">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <p className="text-sm font-medium">{item.product_name}</p>
                              <p className="text-xs text-gray-600 mt-1">
                                ราคา: ฿{parseFloat(item.price || 0).toLocaleString('th-TH', {minimumFractionDigits: 2})} | 
                                จำนวน: {item.quantity} {item.unit}
                              </p>
                              {item.skus && item.skus.length > 0 && (
                                <p className="text-xs text-blue-600 mt-1">
                                  ({item.skus.length} SKUs)
                                </p>
                              )}
                            </div>
                            <button
                              type="button"
                              onClick={() => removeItem(index)}
                              className="ml-2 text-red-600 hover:text-red-800"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Submit Buttons */}
            <div className="flex gap-2 justify-end pt-4 border-t">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setPriceMode(null);
                  setEditingProjectId(null);
                  setEmployeeSearchTerm('');
                  setEmployeeDisplayName('');
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50"
              >
                ยกเลิก
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                {editingProjectId ? 'อัพเดท' : 'บันทึก'}
              </button>
            </div>
          </form>
          )}
        </div>
      )}

      {/* Filter Modal */}
      {showFilterModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[85vh] flex flex-col">
            {/* Header - Fixed */}
            <div className="p-6 border-b flex-shrink-0">
              <h2 className="text-xl font-bold">เลือกสินค้าตาม Filter</h2>
            </div>

            {/* Content - Scrollable */}
            <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-4">
              {/* Categories - Checkbox Style */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  ประเภทสินค้า *
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {CATEGORY_OPTIONS.map(cat => (
                    <label
                      key={cat.value}
                      className={`flex items-center border rounded-lg px-3 py-2 cursor-pointer transition-colors ${
                        filterCriteria.categories.includes(cat.value)
                          ? 'border-red-500 bg-red-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={filterCriteria.categories.includes(cat.value)}
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

              {/* MultiSelect Dropdowns - Show only if category selected */}
              {filterCriteria.categories?.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <MultiSelectDropdown
                    label="Brand"
                    options={filterOptions.brands}
                    selectedValues={filterCriteria.brands}
                    onToggle={(value) => handleFilterToggle('brands', value)}
                    isOpen={openDropdown.brands}
                    onOpen={() => setOpenDropdown(prev => ({ ...prev, brands: true }))}
                    onClose={() => setOpenDropdown(prev => ({ ...prev, brands: false }))}
                  />

                  <MultiSelectDropdown
                    label="Group"
                    options={filterOptions.groups}
                    selectedValues={filterCriteria.groups}
                    onToggle={(value) => handleFilterToggle('groups', value)}
                    isOpen={openDropdown.groups}
                    onOpen={() => setOpenDropdown(prev => ({ ...prev, groups: true }))}
                    onClose={() => setOpenDropdown(prev => ({ ...prev, groups: false }))}
                  />

                  <MultiSelectDropdown
                    label="SubGroup"
                    options={filterOptions.subGroups}
                    selectedValues={filterCriteria.subGroups}
                    onToggle={(value) => handleFilterToggle('subGroups', value)}
                    isOpen={openDropdown.subGroups}
                    onOpen={() => setOpenDropdown(prev => ({ ...prev, subGroups: true }))}
                    onClose={() => setOpenDropdown(prev => ({ ...prev, subGroups: false }))}
                  />

                  <MultiSelectDropdown
                    label="Color"
                    options={filterOptions.colors}
                    selectedValues={filterCriteria.colors}
                    onToggle={(value) => handleFilterToggle('colors', value)}
                    isOpen={openDropdown.colors}
                    onOpen={() => setOpenDropdown(prev => ({ ...prev, colors: true }))}
                    onClose={() => setOpenDropdown(prev => ({ ...prev, colors: false }))}
                  />

                  <MultiSelectDropdown
                    label="Thickness"
                    options={filterOptions.thicknesses}
                    selectedValues={filterCriteria.thicknesses}
                    onToggle={(value) => handleFilterToggle('thicknesses', value)}
                    isOpen={openDropdown.thickness}
                    onOpen={() => setOpenDropdown(prev => ({ ...prev, thickness: true }))}
                    onClose={() => setOpenDropdown(prev => ({ ...prev, thickness: false }))}
                  />
                </div>
              )}

              {/* Loading State */}
              {loadingSkus && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                  <p className="text-blue-700">กำลังค้นหา SKU ที่ตรงกับเงื่อนไข...</p>
                </div>
              )}

              {/* Matched SKUs Display with Global Price Input */}
              {!loadingSkus && matchedSkus.length > 0 && (
                <div className="space-y-3">
                  {/* SKU List - Compact with Scroll */}
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <p className="text-green-800 font-semibold mb-2 text-sm">
                      ✅ พบ {matchedSkus.length} SKU ที่ตรงกับเงื่อนไข
                    </p>
                    <div className="max-h-64 overflow-y-auto space-y-1 bg-white rounded p-2">
                      {matchedSkus.map((item, idx) => (
                        <div key={idx} className="flex items-center justify-between text-xs text-gray-700 hover:bg-gray-50 p-1 rounded group">
                          <span className="flex-1">
                            • {item.sku} - {item.description}
                          </span>
                          <button
                            type="button"
                            onClick={() => removeMatchedSku(item.sku)}
                            className="ml-2 text-red-600 hover:text-red-800 opacity-0 group-hover:opacity-100 transition-opacity"
                            title="ลบรายการนี้"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Global Price and Quantity Input - Compact */}
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-blue-800 font-semibold mb-2 text-sm">
                      📝 กรอกราคา หน่วย และจำนวน
                    </p>
                    
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          ราคา *
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="0.00"
                          value={globalPrice}
                          onChange={(e) => setGlobalPrice(e.target.value)}
                          className="w-full border rounded-lg px-3 py-2 font-semibold border-red-300 focus:border-red-500 focus:ring-red-500"
                          required
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          หน่วย *
                        </label>
                        <select
                          value={globalUnit}
                          onChange={(e) => setGlobalUnit(e.target.value)}
                          className="w-full border rounded-lg px-3 py-2 border-red-300 focus:border-red-500 focus:ring-red-500"
                          required
                        >
                          <option value="">-- เลือกหน่วย --</option>
                          {UNIT_OPTIONS.map((unit) => (
                            <option key={unit.value} value={unit.value}>
                              {unit.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          จำนวน
                        </label>
                        <input
                          type="number"
                          step="0.01"
                          placeholder="0"
                          value={globalQuantity}
                          onChange={(e) => setGlobalQuantity(e.target.value)}
                          className="w-full border rounded-lg px-3 py-2"
                        />
                      </div>
                    </div>

                    <p className="text-xs text-gray-500 mt-2">
                      💡 ใช้กับสินค้าทั้งหมด {matchedSkus.length} รายการ (Brand, ความหนา ดึงจาก SKU)
                    </p>
                  </div>
                </div>
              )}

              {/* No Results */}
              {!loadingSkus && matchedSkus.length === 0 && filterCriteria.categories.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-yellow-800 text-sm">
                    ⚠️ ไม่พบ SKU ที่ตรงกับเงื่อนไข
                  </p>
                </div>
              )}
            </div>
            </div>

            {/* Footer - Fixed */}
            <div className="flex gap-2 justify-between p-4 border-t flex-shrink-0 bg-gray-50">
              <button
                type="button"
                onClick={clearAllFilters}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100 text-sm font-medium"
              >
                ล้างทั้งหมด
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowFilterModal(false);
                    clearAllFilters();
                  }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  ยกเลิก
                </button>
                <button
                  type="button"
                  onClick={addItemsFromFilter}
                  disabled={matchedSkus.length === 0 || !globalPrice || parseFloat(globalPrice) <= 0}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  เพิ่มสินค้า {matchedSkus.length > 0 && `(${matchedSkus.length} รายการ)`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Projects List */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-4 border-b">
          <h2 className="text-xl font-semibold">รายการราคาโครงการ</h2>
        </div>
        
        {loading ? (
          <div className="p-8 text-center text-gray-500">กำลังโหลด...</div>
        ) : filteredProjects.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {customerSearchTerm ? 'ไม่พบโครงการที่ตรงกับคำค้นหา' : 'ยังไม่มีข้อมูลราคาโครงการ'}
          </div>
        ) : (
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {filteredProjects.map((project) => (
              <div key={project.project_id} className="p-4 hover:bg-gray-50">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h3 className="font-semibold text-lg">{project.project_code}</h3>
                    {project.project_name && (
                      <p className="text-gray-600">{project.project_name}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {project.status !== 'canceled' && (
                      <button
                        onClick={() => startEditProject(project)}
                        className="text-blue-600 hover:text-blue-800 px-2 py-1 border rounded-md font-bold"
                      >
                        แก้ไข
                      </button>
                    )}
                    <select
                      value={project.status}
                      onChange={(e) => updateStatus(project.project_id, e.target.value)}
                      className={`px-2 py-1 rounded text-sm font-medium ${
                        project.status === 'active' ? 'bg-white text-green-800' :
                        project.status === 'expired' ? 'bg-gray-100 text-gray-800' :
                        project.status === 'canceled' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}
                    >
                      <option value="active">Active</option>
                      <option value="expired">Expired</option>
                      <option value="canceled">Canceled</option>
                    </select>
                    <button
                      onClick={() => deleteProject(project.project_id)}
                      className="text-red-600 hover:text-red-800"
                      title="ยกเลิกราคาโครงการ"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 text-sm text-gray-600 mb-3">
                  <div className="flex items-center gap-1">
                    <User className="w-4 h-4" />
                    <span className="truncate">{project.customer_name || project.customer_code || '-'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Building2 className="w-4 h-4" />
                    <span className="truncate">สาขา: {project.branch_code || '-'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    <span className="truncate">{project.price_start_date} - {project.price_end_date}</span>
                  </div>
                  <div className="truncate">
                    <span>ผู้ขอ: {project.request_by || '-'}</span>
                  </div>
                </div>

                {/* ⭐ แสดง Remark */}
                {project.remark && (
                  <div className="bg-blue-50 border-l-4 border-blue-400 p-2 mb-3 rounded">
                    <p className="text-xs font-semibold text-blue-800 mb-1">รายการสินค้าที่ขอราคาพิเศษ:</p>
                    <p className="text-sm text-blue-700">{project.remark}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// MultiSelectDropdown Component
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
    e.stopPropagation();
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
          {selectedValues.slice(0, 5).map((value) => {
            const label = options.find(opt => opt.value === value)?.label || value;
            return (
              <span
                key={value}
                className="bg-red-50 text-red-700 text-xs px-2 py-1 rounded-full"
              >
                {label}
              </span>
            );
          })}
          {selectedValues.length > 5 && (
            <span className="bg-gray-100 text-gray-600 text-xs px-2 py-1 rounded-full">
              +{selectedValues.length - 5} อื่นๆ
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

export default ProjectPriceManagement;
