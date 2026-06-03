<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASA - Aceh Sentimen Analisis</title>
    
    <!-- Load Google Fonts (Inter) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- Load Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    
    <!-- Load Chart.js for visualizations -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Load Phosphor Icons -->
    <script src="https://unpkg.com/@phosphor-icons/web"></script>

    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Inter', 'sans-serif'] },
                    colors: {
                        primary: '#0ea5e9', // Sky blue
                        secondary: '#0f172a', // Slate 900
                        sentiment: { pos: '#10b981', neg: '#f43f5e', neu: '#64748b' }
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .view-section { animation: fadeIn 0.3s ease-in-out; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(5px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body class="text-slate-800 antialiased flex h-screen overflow-hidden">

    <aside class="w-64 bg-secondary border-r border-slate-800 hidden md:flex flex-col h-full shadow-lg z-20 text-slate-300">
        <!-- Brand Header -->
        <div class="p-6 border-b border-slate-800 flex items-center gap-3 bg-slate-900">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white font-black text-xl shadow-md">
                A
            </div>
            <div>
                <h1 class="font-bold text-lg tracking-wide text-white leading-tight">ASA</h1>
                <p class="text-[10px] text-slate-400 uppercase tracking-wider">Aceh Sentimen Analisis</p>
            </div>
        </div>

        <!-- Navigation -->
        <nav class="flex-1 p-4 space-y-1 overflow-y-auto" id="sidebar-nav">
            <p class="px-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 mt-2">Analitik Utama</p>
            <a href="#" data-target="dashboard" class="nav-item active-nav flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium text-sm transition-colors bg-primary/20 text-white border border-primary/30">
                <i class="ph ph-chart-polar text-lg text-primary"></i> Dashboard Isu
            </a>
            
            <p class="px-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 mt-6">Manajemen & Konfigurasi</p>
            <a href="#" data-target="issues" class="nav-item flex items-center gap-3 px-3 py-2.5 text-slate-400 hover:bg-slate-800 hover:text-white rounded-lg font-medium text-sm transition-colors">
                <i class="ph ph-folders text-lg"></i> Manajemen Isu <span class="ml-auto bg-slate-800 text-xs py-0.5 px-2 rounded-full">3</span>
            </a>
            <a href="#" data-target="sources" class="nav-item flex items-center gap-3 px-3 py-2.5 text-slate-400 hover:bg-slate-800 hover:text-white rounded-lg font-medium text-sm transition-colors">
                <i class="ph ph-database text-lg"></i> Integrasi Data
            </a>
            <a href="#" data-target="reports" class="nav-item flex items-center gap-3 px-3 py-2.5 text-slate-400 hover:bg-slate-800 hover:text-white rounded-lg font-medium text-sm transition-colors">
                <i class="ph ph-file-pdf text-lg"></i> Ekspor Laporan
            </a>
        </nav>

        <!-- Agent Status -->
        <div class="p-4 border-t border-slate-800 bg-slate-900/50">
            <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-primary">
                    <i class="ph ph-robot text-xl"></i>
                </div>
                <div class="flex-1">
                    <p class="text-sm font-semibold text-slate-200">Antygravity Agent</p>
                    <p class="text-[11px] text-emerald-400 flex items-center gap-1.5">
                        <span class="relative flex h-2 w-2">
                          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        Monitoring Aktif
                    </p>
                </div>
            </div>
        </div>
    </aside>

    <main class="flex-1 flex flex-col h-full overflow-hidden relative">
        <!-- Top Header -->
        <header class="bg-white border-b border-slate-200 h-16 flex items-center justify-between px-4 sm:px-6 z-10 shrink-0 shadow-sm">
            <div class="flex items-center gap-3">
                <button class="md:hidden text-slate-500 hover:text-slate-800">
                    <i class="ph ph-list text-2xl"></i>
                </button>
                <div class="hidden sm:flex items-center gap-2 text-sm font-medium text-slate-500">
                    <i class="ph ph-hash text-slate-400"></i> Fokus Isu Saat Ini:
                </div>
                <!-- Issue Selector Dropdown -->
                <select class="bg-slate-50 border border-slate-200 text-slate-800 text-sm font-bold rounded-lg focus:ring-primary focus:border-primary block p-2 outline-none cursor-pointer">
                    <option value="otsus">Dana Otsus Aceh</option>
                    <option value="jalan">Infrastruktur & Jalan Rusak</option>
                    <option value="pilkada">Pilkada Gubernur 2026</option>
                </select>
            </div>
            
            <div class="flex items-center gap-4">
                <div class="hidden lg:flex items-center text-xs text-slate-500 font-medium">
                    <i class="ph ph-clock mr-1"></i> Update: 5 mnt lalu
                </div>
                <button onclick="showToast('Agen sedang menyinkronkan data terbaru dari semua platform...')" class="bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center gap-2">
                    <i class="ph ph-arrows-clockwise"></i> <span class="hidden sm:inline">Sinkronisasi</span>
                </button>
            </div>
        </header>

        <!-- Main Content Area -->
        <div class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 hide-scrollbar bg-slate-50 relative">
            
            <!-- VIEW: DASHBOARD (ISSUE FOCUS) -->
            <div id="view-dashboard" class="view-section block">
                
                <div class="mb-6 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
                    <div>
                        <h2 class="text-2xl font-bold text-slate-800 tracking-tight">Analisis: Dana Otsus Aceh</h2>
                        <p class="text-sm text-slate-500 mt-1">Menampilkan agregasi sentimen spesifik untuk isu ini dalam 7 hari terakhir.</p>
                    </div>
                    <div class="flex bg-white rounded-lg border border-slate-200 p-1 shadow-sm w-fit">
                        <button class="px-3 py-1.5 text-xs font-medium bg-slate-100 text-slate-800 rounded-md">7 Hari</button>
                        <button class="px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 rounded-md transition-colors">30 Hari</button>
                    </div>
                </div>

                <!-- Issue KPIs -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full bg-blue-50 text-primary flex items-center justify-center text-xl"><i class="ph ph-database"></i></div>
                        <div>
                            <p class="text-xs font-medium text-slate-500">Total Data Isu</p>
                            <h3 class="text-xl font-bold text-slate-800">12.450</h3>
                        </div>
                    </div>
                    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full bg-rose-50 text-rose-500 flex items-center justify-center text-xl"><i class="ph ph-trend-down"></i></div>
                        <div>
                            <p class="text-xs font-medium text-slate-500">Sentimen Negatif</p>
                            <h3 class="text-xl font-bold text-slate-800">58%</h3>
                        </div>
                    </div>
                    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center text-xl"><i class="ph ph-minus"></i></div>
                        <div>
                            <p class="text-xs font-medium text-slate-500">Sentimen Netral</p>
                            <h3 class="text-xl font-bold text-slate-800">27%</h3>
                        </div>
                    </div>
                    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full bg-emerald-50 text-emerald-500 flex items-center justify-center text-xl"><i class="ph ph-trend-up"></i></div>
                        <div>
                            <p class="text-xs font-medium text-slate-500">Sentimen Positif</p>
                            <h3 class="text-xl font-bold text-slate-800">15%</h3>
                        </div>
                    </div>
                </div>

                <!-- Platform Breakdown section -->
                <h3 class="font-semibold text-slate-800 mb-4 text-sm uppercase tracking-wider">Komparasi Per Platform</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    
                    <!-- Platform: Portal Berita -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
                        <div class="flex justify-between items-start mb-6">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-xl"><i class="ph ph-browser"></i></div>
                                <div>
                                    <h4 class="font-bold text-slate-800">Portal Berita</h4>
                                    <p class="text-xs text-slate-500">Serambi, AJNN, dll</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="text-lg font-bold text-slate-800">3.210</span>
                                <p class="text-[10px] text-slate-400 uppercase">Artikel</p>
                            </div>
                        </div>
                        
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-emerald-600">Pos 45%</span>
                                <span class="text-slate-500">Neu 40%</span>
                                <span class="text-rose-600">Neg 15%</span>
                            </div>
                            <div class="w-full h-2.5 bg-slate-100 rounded-full flex overflow-hidden">
                                <div class="bg-emerald-500 h-full transition-all duration-1000" style="width: 45%"></div>
                                <div class="bg-slate-400 h-full transition-all duration-1000" style="width: 40%"></div>
                                <div class="bg-rose-500 h-full transition-all duration-1000" style="width: 15%"></div>
                            </div>
                            <p class="text-xs text-slate-500 pt-2 border-t border-slate-100 mt-3 italic">
                                Mayoritas meliput pernyataan resmi pemerintah & alokasi dana secara netral.
                            </p>
                        </div>
                    </div>

                    <!-- Platform: TikTok -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-slate-900"></div>
                        <div class="flex justify-between items-start mb-6">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-slate-100 text-slate-900 flex items-center justify-center text-xl"><i class="ph ph-tiktok-logo"></i></div>
                                <div>
                                    <h4 class="font-bold text-slate-800">TikTok</h4>
                                    <p class="text-xs text-slate-500">Video & Komentar</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="text-lg font-bold text-slate-800">5.840</span>
                                <p class="text-[10px] text-slate-400 uppercase">Data</p>
                            </div>
                        </div>
                        
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-emerald-600">Pos 5%</span>
                                <span class="text-slate-500">Neu 15%</span>
                                <span class="text-rose-600">Neg 80%</span>
                            </div>
                            <div class="w-full h-2.5 bg-slate-100 rounded-full flex overflow-hidden">
                                <div class="bg-emerald-500 h-full transition-all duration-1000" style="width: 5%"></div>
                                <div class="bg-slate-400 h-full transition-all duration-1000" style="width: 15%"></div>
                                <div class="bg-rose-500 h-full transition-all duration-1000" style="width: 80%"></div>
                            </div>
                            <p class="text-xs text-slate-500 pt-2 border-t border-slate-100 mt-3 italic">
                                Sangat reaktif. Banyak konten kreator mengkritik realisasi dana di lapangan.
                            </p>
                        </div>
                    </div>

                    <!-- Platform: Meta (FB/IG) -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
                        <div class="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-purple-500 to-pink-500"></div>
                        <div class="flex justify-between items-start mb-6">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-pink-50 text-pink-600 flex items-center justify-center text-xl"><i class="ph ph-instagram-logo"></i></div>
                                <div>
                                    <h4 class="font-bold text-slate-800">Meta (FB & IG)</h4>
                                    <p class="text-xs text-slate-500">Post & Grup Publik</p>
                                </div>
                            </div>
                            <div class="text-right">
                                <span class="text-lg font-bold text-slate-800">3.400</span>
                                <p class="text-[10px] text-slate-400 uppercase">Data</p>
                            </div>
                        </div>
                        
                        <div class="space-y-2">
                            <div class="flex justify-between text-xs font-medium">
                                <span class="text-emerald-600">Pos 15%</span>
                                <span class="text-slate-500">Neu 25%</span>
                                <span class="text-rose-600">Neg 60%</span>
                            </div>
                            <div class="w-full h-2.5 bg-slate-100 rounded-full flex overflow-hidden">
                                <div class="bg-emerald-500 h-full transition-all duration-1000" style="width: 15%"></div>
                                <div class="bg-slate-400 h-full transition-all duration-1000" style="width: 25%"></div>
                                <div class="bg-rose-500 h-full transition-all duration-1000" style="width: 60%"></div>
                            </div>
                            <p class="text-xs text-slate-500 pt-2 border-t border-slate-100 mt-3 italic">
                                Diskusi panjang di grup FB lokal. Sentimen didominasi skeptisisme masyarakat.
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Time-Series Chart & Feed -->
                <div class="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-8">
                    <!-- Chart -->
                    <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm xl:col-span-2">
                        <div class="flex justify-between items-center mb-4">
                            <div>
                                <h3 class="font-bold text-slate-800">Tren Sentimen (Time-Series)</h3>
                                <p class="text-xs text-slate-500">Pergerakan sentimen untuk isu Dana Otsus 7 hari terakhir</p>
                            </div>
                        </div>
                        <div class="relative h-72 w-full">
                            <canvas id="timeSeriesChart"></canvas>
                        </div>
                    </div>

                    <!-- Live Feed -->
                    <div class="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col h-full">
                        <div class="flex justify-between items-center mb-4">
                            <h3 class="font-bold text-slate-800">Live Feed Agen</h3>
                            <span class="flex h-3 w-3 relative">
                                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                            </span>
                        </div>
                        <div class="flex-1 overflow-y-auto pr-2 space-y-3">
                            <!-- Dummy Data 1 -->
                            <div class="p-3 rounded-lg border border-rose-100 bg-rose-50/50">
                                <div class="flex justify-between items-start mb-1.5">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700">NEG (92%)</span>
                                    <div class="flex items-center gap-1 text-[10px] font-medium text-slate-500">
                                        <i class="ph ph-tiktok-logo text-slate-900"></i> TikTok • 2 mnt lalu
                                    </div>
                                </div>
                                <p class="text-xs text-slate-700 leading-relaxed">"Otsus besar tapi jalan ke kampung kami masih hancur berdebu. Uangnya kemana semua ini petinggi?"</p>
                            </div>
                            <!-- Dummy Data 2 -->
                            <div class="p-3 rounded-lg border border-slate-200 bg-slate-50">
                                <div class="flex justify-between items-start mb-1.5">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-600">NEU (85%)</span>
                                    <div class="flex items-center gap-1 text-[10px] font-medium text-slate-500">
                                        <i class="ph ph-browser text-blue-600"></i> Berita • 15 mnt lalu
                                    </div>
                                </div>
                                <p class="text-xs text-slate-700 leading-relaxed">"Gubernur paparkan evaluasi penyaluran dana otsus tahun 2025 di depan dewan. Terdapat beberapa catatan."</p>
                            </div>
                            <!-- Dummy Data 3 -->
                            <div class="p-3 rounded-lg border border-emerald-100 bg-emerald-50/50">
                                <div class="flex justify-between items-start mb-1.5">
                                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700">POS (78%)</span>
                                    <div class="flex items-center gap-1 text-[10px] font-medium text-slate-500">
                                        <i class="ph ph-instagram-logo text-pink-600"></i> IG • 45 mnt lalu
                                    </div>
                                </div>
                                <p class="text-xs text-slate-700 leading-relaxed">"Alhamdulillah beasiswa yatim dari dana otsus tahun ini sudah cair. Sangat terbantu buat anak sekolah."</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- VIEW: MANAJEMEN ISU (Database of Topics) -->
            <div id="view-issues" class="view-section hidden max-w-5xl mx-auto">
                <div class="mb-6">
                    <h2 class="text-2xl font-bold text-slate-800 tracking-tight">Manajemen Topik & Isu</h2>
                    <p class="text-sm text-slate-500 mt-1">Buat *project* isu baru untuk dipantau oleh agen, atau lihat arsip isu sebelumnya.</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <!-- Form Create New Issue -->
                    <div class="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm h-fit">
                        <div class="flex items-center gap-2 mb-4">
                            <div class="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center"><i class="ph ph-plus-circle text-lg"></i></div>
                            <h3 class="font-bold text-slate-800">Buat Isu Baru</h3>
                        </div>
                        <p class="text-xs text-slate-500 mb-5">Form ini menjadi *trigger* untuk Agen AI membuat struktur tabel baru dan memulai proses *scraping*.</p>
                        
                        <form onsubmit="submitForm(event, 'Isu baru berhasil didaftarkan. Agen sedang mengonfigurasi tracker.')" class="space-y-4">
                            <div>
                                <label class="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Nama Isu/Proyek</label>
                                <input type="text" placeholder="Contoh: Harga Beras Banda Aceh" class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm transition-all" required>
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Kata Kunci Utama (Keywords)</label>
                                <textarea placeholder='["harga beras", "sembako mahal", "pasar aceh"]' rows="3" class="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none text-sm transition-all font-mono text-xs" required></textarea>
                                <p class="text-[10px] text-slate-400 mt-1">Pisahkan dengan koma atau gunakan format array JSON.</p>
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-slate-700 mb-2 uppercase tracking-wide">Platform Target</label>
                                <div class="space-y-2">
                                    <label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked class="rounded text-primary focus:ring-primary"> Portal Berita (Web Scrape)</label>
                                    <label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked class="rounded text-primary focus:ring-primary"> TikTok API</label>
                                    <label class="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked class="rounded text-primary focus:ring-primary"> Meta (Facebook/IG) API</label>
                                </div>
                            </div>
                            <button type="submit" class="w-full bg-secondary hover:bg-slate-800 text-white font-medium py-2.5 rounded-lg text-sm transition-colors mt-4 flex items-center justify-center gap-2">
                                <i class="ph ph-rocket-launch text-lg"></i> Eksekusi Agen
                            </button>
                        </form>
                    </div>

                    <!-- Master Table of Issues -->
                    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm lg:col-span-2 overflow-hidden flex flex-col">
                        <div class="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <h3 class="font-bold text-slate-800">Database Isu (Master Data)</h3>
                            <div class="relative">
                                <i class="ph ph-magnifying-glass absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400"></i>
                                <input type="text" placeholder="Cari isu..." class="pl-9 pr-4 py-1.5 border border-slate-200 rounded-lg text-sm outline-none focus:border-primary w-48 transition-all">
                            </div>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead>
                                    <tr class="bg-white border-b border-slate-200 text-xs text-slate-500 uppercase tracking-wider">
                                        <th class="p-4 font-semibold">Nama Isu</th>
                                        <th class="p-4 font-semibold">Status Agen</th>
                                        <th class="p-4 font-semibold">Total Data</th>
                                        <th class="p-4 font-semibold text-right">Aksi</th>
                                    </tr>
                                </thead>
                                <tbody class="text-sm divide-y divide-slate-100">
                                    <tr class="hover:bg-slate-50 transition-colors">
                                        <td class="p-4">
                                            <p class="font-bold text-slate-800">Dana Otsus Aceh</p>
                                            <p class="text-xs text-slate-500 truncate w-48">["otsus", "dana otonomi khusus"]</p>
                                        </td>
                                        <td class="p-4"><span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">AKTIF (MONITORING)</span></td>
                                        <td class="p-4 font-medium text-slate-600">12.450</td>
                                        <td class="p-4 text-right">
                                            <button class="px-3 py-1.5 bg-primary/10 text-primary hover:bg-primary hover:text-white rounded text-xs font-medium transition-colors">Buka Dashboard</button>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-slate-50 transition-colors">
                                        <td class="p-4">
                                            <p class="font-bold text-slate-800">Infrastruktur & Jalan Rusak</p>
                                            <p class="text-xs text-slate-500 truncate w-48">["jalan rusak", "jalan berlubang", "banjir"]</p>
                                        </td>
                                        <td class="p-4"><span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">AKTIF (MONITORING)</span></td>
                                        <td class="p-4 font-medium text-slate-600">8.920</td>
                                        <td class="p-4 text-right">
                                            <button class="px-3 py-1.5 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-xs font-medium transition-colors">Buka Dashboard</button>
                                        </td>
                                    </tr>
                                    <tr class="hover:bg-slate-50 transition-colors opacity-75">
                                        <td class="p-4">
                                            <p class="font-bold text-slate-800">Pilkada Gubernur 2026</p>
                                            <p class="text-xs text-slate-500 truncate w-48">["pilkada aceh", "cagub", "pemilihan"]</p>
                                        </td>
                                        <td class="p-4"><span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">ARSIP (BERHENTI)</span></td>
                                        <td class="p-4 font-medium text-slate-600">45.100</td>
                                        <td class="p-4 text-right">
                                            <button class="px-3 py-1.5 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-xs font-medium transition-colors">Lihat Data</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- VIEW: SUMBER DATA (Integration config) -->
            <div id="view-sources" class="view-section hidden max-w-4xl mx-auto">
                <div class="mb-6">
                    <h2 class="text-2xl font-bold text-slate-800 tracking-tight">Integrasi & Sumber Data</h2>
                    <p class="text-sm text-slate-500 mt-1">Status koneksi API dan Web Scraper yang dikelola oleh agen di latar belakang.</p>
                </div>
                
                <div class="bg-white rounded-2xl p-2 border border-slate-200 shadow-sm">
                    <!-- Integration Items -->
                    <div class="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors rounded-t-xl">
                        <div class="flex items-center gap-4">
                            <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center text-2xl"><i class="ph ph-browser"></i></div>
                            <div>
                                <h4 class="font-bold text-slate-800">Scraper Portal Berita Lokal</h4>
                                <p class="text-xs text-slate-500 mt-0.5">Metode: HTML DOM Parsing (BeautifulSoup/Playwright)</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-4 sm:flex-col sm:items-end">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">KONEKSI STABIL</span>
                            <span class="text-xs text-slate-400">Sinkronisasi terakhir: 5 mnt lalu</span>
                        </div>
                    </div>

                    <div class="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors">
                        <div class="flex items-center gap-4">
                            <div class="w-12 h-12 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center text-2xl"><i class="ph ph-tiktok-logo"></i></div>
                            <div>
                                <h4 class="font-bold text-slate-800">TikTok API (Unofficial)</h4>
                                <p class="text-xs text-slate-500 mt-0.5">Metode: Keyword & Hashtag Tracker via Python Tool</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-4 sm:flex-col sm:items-end">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">KONEKSI STABIL</span>
                            <span class="text-xs text-slate-400">Sinkronisasi terakhir: 12 mnt lalu</span>
                        </div>
                    </div>

                    <div class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors rounded-b-xl">
                        <div class="flex items-center gap-4">
                            <div class="w-12 h-12 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center text-2xl"><i class="ph ph-instagram-logo"></i></div>
                            <div>
                                <h4 class="font-bold text-slate-800">Meta Graph API (FB/IG)</h4>
                                <p class="text-xs text-slate-500 mt-0.5">Metode: Official API (Butuh rotasi Access Token)</p>
                            </div>
                        </div>
                        <div class="flex items-center gap-4 sm:flex-col sm:items-end">
                            <span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700">RATE LIMITED</span>
                            <span class="text-xs text-slate-400">Menunggu reset dari server Meta</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- VIEW: EKSPOR LAPORAN -->
            <div id="view-reports" class="view-section hidden max-w-2xl mx-auto">
                <div class="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm text-center">
                    <div class="w-16 h-16 bg-blue-50 text-primary rounded-full flex items-center justify-center mx-auto mb-4 border border-blue-100 shadow-inner">
                        <i class="ph ph-file-pdf text-3xl"></i>
                    </div>
                    <h3 class="font-bold text-xl text-slate-800 mb-2">Automasi Laporan Eksekutif</h3>
                    <p class="text-sm text-slate-500 mb-8">Agen AI akan mengumpulkan data isu terpilih, menganalisis kesimpulan utama, dan men-generate laporan PDF rapi untuk pimpinan.</p>

                    <form onsubmit="submitForm(event, 'Permintaan Diterima. Agen AI sedang menyusun Laporan PDF Anda.')" class="space-y-5 text-left max-w-md mx-auto">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Pilih Isu</label>
                            <select class="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary outline-none text-sm">
                                <option>Dana Otsus Aceh</option>
                                <option>Infrastruktur & Jalan Rusak</option>
                            </select>
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 mb-1 uppercase tracking-wide">Analisis Kedalaman AI</label>
                            <select class="w-full px-4 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary outline-none text-sm">
                                <option>Standar (Grafik & Ringkasan)</option>
                                <option>Mendalam (Sertakan Ekstraksi Topik Kunci & Rekomendasi)</option>
                            </select>
                        </div>
                        <button type="submit" class="w-full bg-primary hover:bg-blue-600 text-white font-medium py-3 rounded-lg text-sm transition-colors mt-2 flex items-center justify-center gap-2 shadow-sm">
                            <i class="ph ph-magic-wand text-lg"></i> Generate Laporan PDF
                        </button>
                    </form>
                </div>
            </div>

        </div>
    </main>

    <!-- Toast Notification -->
    <div id="toast" class="fixed bottom-5 right-5 transform translate-y-20 opacity-0 transition-all duration-300 bg-secondary text-white px-5 py-3 rounded-xl shadow-2xl flex items-center gap-3 z-50 border border-slate-700">
        <i class="ph ph-check-circle text-emerald-400 text-xl"></i>
        <span id="toast-message" class="text-sm font-medium">Notifikasi berhasil!</span>
    </div>

    <script>
        // 1. Navigation Logic (SPA Routing)
        const navItems = document.querySelectorAll('.nav-item');
        const views = document.querySelectorAll('.view-section');

        navItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Get target
                const target = item.getAttribute('data-target');
                
                // Hide all views
                views.forEach(view => {
                    view.classList.add('hidden');
                    view.classList.remove('block');
                });
                
                // Show target view
                document.getElementById('view-' + target).classList.remove('hidden');
                document.getElementById('view-' + target).classList.add('block');

                // Update styling
                navItems.forEach(nav => {
                    nav.classList.remove('bg-primary/20', 'text-white', 'border', 'border-primary/30', 'active-nav');
                    nav.classList.add('text-slate-400');
                    const icon = nav.querySelector('i');
                    if(icon) icon.classList.remove('text-primary');
                });
                
                item.classList.remove('text-slate-400');
                item.classList.add('bg-primary/20', 'text-white', 'border', 'border-primary/30', 'active-nav');
                const activeIcon = item.querySelector('i');
                if(activeIcon) activeIcon.classList.add('text-primary');
            });
        });

        // 2. Form Mockup & Toast Logic
        function submitForm(event, message) {
            event.preventDefault();
            showToast(message);
        }

        function showToast(message) {
            const toast = document.getElementById('toast');
            document.getElementById('toast-message').textContent = message;
            toast.classList.remove('translate-y-20', 'opacity-0');
            setTimeout(() => {
                toast.classList.add('translate-y-20', 'opacity-0');
            }, 3500);
        }

        // 3. Init Chart.js for Time-Series specific to the Issue
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.color = '#94a3b8';
        
        const ctx = document.getElementById('timeSeriesChart').getContext('2d');
        
        // Gradient for Negative Area
        const gradientNeg = ctx.createLinearGradient(0, 0, 0, 400);
        gradientNeg.addColorStop(0, 'rgba(244, 63, 94, 0.2)'); // Rose
        gradientNeg.addColorStop(1, 'rgba(244, 63, 94, 0)');

        // Gradient for Positive Area
        const gradientPos = ctx.createLinearGradient(0, 0, 0, 400);
        gradientPos.addColorStop(0, 'rgba(16, 185, 129, 0.2)'); // Emerald
        gradientPos.addColorStop(1, 'rgba(16, 185, 129, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['28 Mei', '29 Mei', '30 Mei', '31 Mei', '1 Jun', '2 Jun', 'Hari Ini'],
                datasets: [
                    {
                        label: 'Sentimen Negatif (Kritik/Keluhan)',
                        data: [420, 500, 480, 850, 1200, 950, 800], // Spike in negative sentiment
                        borderColor: '#f43f5e',
                        backgroundColor: gradientNeg,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#f43f5e',
                        pointBorderColor: '#fff',
                        pointRadius: 4
                    },
                    {
                        label: 'Sentimen Positif (Apresiasi)',
                        data: [200, 220, 210, 190, 205, 180, 195], // Relatively flat positive sentiment
                        borderColor: '#10b981',
                        backgroundColor: gradientPos,
                        borderWidth: 2,
                        tension: 0.4,
                        fill: true,
                        pointBackgroundColor: '#10b981',
                        pointBorderColor: '#fff',
                        pointRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        align: 'end',
                        labels: { boxWidth: 8, usePointStyle: true, font: { weight: '600' } }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleFont: { size: 13 },
                        bodyFont: { size: 13 },
                        padding: 10,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        grid: { display: false, drawBorder: false }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#f1f5f9', borderDash: [5, 5], drawBorder: false }
                    }
                },
                interaction: { mode: 'nearest', axis: 'x', intersect: false }
            }
        });
    </script>
</body>
</html>