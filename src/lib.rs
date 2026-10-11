use pyo3::prelude::*;
use ahash::AHashSet as HashSet;
use serde::{Serialize, Deserialize};
use std::collections::VecDeque;

// ═══════════════════════════════════════════════════════════
// BUBBLE ENGINE — Pencocokan, Konektivitas, Grid
// Menggantikan fungsi Python yang lambat → instan di Rust
// ═══════════════════════════════════════════════════════════
//
// CATATAN TIPE: grid pakai Option<i32>, BUKAN Option<u32>.
// Kenapa: di Python, cell bisa berisi -1 (rainbow bubble / wildcard)
// atau -3 (boss sentinel). u32 gak bisa nampung nilai negatif itu,
// jadi wajib i32 biar match logic (c == -1 dst) valid & konsisten
// sama semantik game aslinya.

// ═══════════════════════════════════════════════
// BAGIAN 1: PENCARIAN BUBBLE YANG COCOK (Flood-Fill)
// ═══════════════════════════════════════════════

/// Ambil daftar tetangga berdasarkan baris genap/ganjil
#[inline(always)]
fn get_neighbors(row: usize, col: usize, rows: usize, cols: usize) -> Vec<(usize, usize)> {
    let mut result = Vec::with_capacity(6);
    
    // Explicitly annotate the type here, allowing Rust to infer the literals as `isize`
    let directions: &[(isize, isize)] = if row % 2 == 0 {
        &[(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
    } else {
        &[(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
    };

    for &(dr, dc) in directions {
        let nr = row as isize + dr;
        let nc = col as isize + dc;
        if nr >= 0 && nr < rows as isize && nc >= 0 && nc < cols as isize {
            result.push((nr as usize, nc as usize));
        }
    }
    result
}

/// Cari semua bubble yang terhubung warnanya (BFS — lebih cepat dari rekursif!)
/// Sama persis semantiknya dengan Scene.find_matching di Python:
/// cocok kalau warnanya sama, ATAU salah satu sisi adalah -1 (rainbow wildcard).
#[pyfunction]
fn find_matching(
    grid: Vec<Vec<Option<i32>>>,
    start_row: usize,
    start_col: usize,
) -> Vec<(usize, usize)> {
    let rows = grid.len();
    if rows == 0 { return Vec::new(); }
    let cols = grid[0].len();

    let target_color = match grid.get(start_row).and_then(|r| r.get(start_col)) {
        Some(&Some(c)) => c,
        _ => return Vec::new(),
    };

    let mut visited = HashSet::with_capacity(rows * cols / 4);
    let mut queue = VecDeque::new();
    let mut result = Vec::with_capacity(16);

    queue.push_back((start_row, start_col));
    visited.insert((start_row, start_col));

    while let Some((row, col)) = queue.pop_front() {
        result.push((row, col));

        for (nr, nc) in get_neighbors(row, col, rows, cols) {
            if !visited.contains(&(nr, nc)) {
                match grid.get(nr).and_then(|r| r.get(nc)) {
                    Some(&Some(c)) if c == target_color || c == -1 || target_color == -1 => {
                        visited.insert((nr, nc));
                        queue.push_back((nr, nc));
                    }
                    _ => {}
                }
            }
        }
    }

    result
}

// ═══════════════════════════════════════════════
// BAGIAN 2: KONEKTIVITAS (TERHUBUNG LANGIT-LANGIT / DARI TITIK MANAPUN)
// ═══════════════════════════════════════════════

/// Flood-fill generik atas cell TERISI (warna apapun, gak peduli), mulai
/// dari sekumpulan titik awal. Dipakai buat dua kasus: konektivitas ke
/// langit-langit (start = semua col di baris 0), dan cluster dari satu
/// titik sembarang (start = 1 titik).
fn flood_fill_occupied(
    grid: &[Vec<Option<i32>>],
    starts: Vec<(usize, usize)>,
) -> HashSet<(usize, usize)> {
    let rows = grid.len();
    if rows == 0 { return HashSet::new(); }
    let cols = grid[0].len();

    let mut visited = HashSet::with_capacity(rows * cols / 2);
    let mut queue = VecDeque::new();

    for s in starts {
        if let Some(Some(_)) = grid.get(s.0).and_then(|r| r.get(s.1)) {
            visited.insert(s);
            queue.push_back(s);
        }
    }

    while let Some((row, col)) = queue.pop_front() {
        for (nr, nc) in get_neighbors(row, col, rows, cols) {
            if !visited.contains(&(nr, nc)) {
                if let Some(Some(_)) = grid.get(nr).and_then(|r| r.get(nc)) {
                    visited.insert((nr, nc));
                    queue.push_back((nr, nc));
                }
            }
        }
    }

    visited
}

/// Cari semua bubble yang TERHUBUNG ke langit-langit (baris 0)
fn find_connected_to_top(grid: &[Vec<Option<i32>>]) -> HashSet<(usize, usize)> {
    let cols = if grid.is_empty() { 0 } else { grid[0].len() };
    let starts: Vec<(usize, usize)> = (0..cols).map(|c| (0usize, c)).collect();
    flood_fill_occupied(grid, starts)
}

/// Kembalikan daftar posisi bubble yang MENGAMBANG (tidak nyambung ke atas).
/// Menggantikan Scene.remove_floating_bubbles (loop find_connected + loop cek).
#[pyfunction]
fn find_floating_bubbles(grid: Vec<Vec<Option<i32>>>) -> Vec<(usize, usize)> {
    let rows = grid.len();
    if rows == 0 { return Vec::new(); }
    let cols = grid[0].len();

    let connected = find_connected_to_top(&grid);
    let mut floating = Vec::new();

    for row in 0..rows {
        for col in 0..cols {
            if let Some(Some(_)) = grid[row].get(col) {
                if !connected.contains(&(row, col)) {
                    floating.push((row, col));
                }
            }
        }
    }

    floating
}

/// Cari cluster bubble terisi yang terhubung dari satu titik (row, col),
/// TANPA peduli warna. Menggantikan Scene.find_connected_cluster /
/// Scene.find_connected (versi rekursif Python, rawan RecursionError di
/// grid besar).
#[pyfunction]
fn find_connected_cluster(
    grid: Vec<Vec<Option<i32>>>,
    start_row: usize,
    start_col: usize,
) -> Vec<(usize, usize)> {
    flood_fill_occupied(&grid, vec![(start_row, start_col)])
        .into_iter()
        .collect()
}

// ═══════════════════════════════════════════════
// BAGIAN 3: TETANGGA GRID
// ═══════════════════════════════════════════════

#[pyfunction]
fn get_neighbors_list(row: usize, col: usize, rows: usize, cols: usize) -> Vec<(usize, usize)> {
    get_neighbors(row, col, rows, cols)
}

// ═══════════════════════════════════════════════
// BAGIAN 4: SAVE/LOAD GAME (JSON CEPAT)
// ═══════════════════════════════════════════════
//
// CATATAN: struct ini cuma nyimpen subset ringan (score/level/
// shots_until_drop/grid). Save data lengkap di macan_bubble_shooter36.py
// (save_game/load_game_data) juga nyimpen high_score, shooter_current/
// next, powerups dict, playtime, total_shots, total_pops, best_combo —
// field itu BELUM ada di sini. Jangan langsung swap save_game() Python
// ke fungsi ini tanpa nambahin field-field itu dulu, nanti data hilang
// pas load. Untuk sekarang dibiarkan sebagai util ringan/opsional; save
// utama tetap json.dump biasa di Python (sudah cukup cepat, dipanggil
// jarang, gak perlu Rust).

#[derive(Serialize, Deserialize)]
struct SaveData {
    score: i64,
    level: u32,
    shots_until_drop: u32,
    grid: Vec<Vec<Option<i32>>>,
    timestamp: i64,
}

#[pyfunction]
fn serialize_game_state(
    grid: Vec<Vec<Option<i32>>>,
    score: i64,
    level: u32,
    shots_until_drop: u32,
) -> PyResult<String> {
    let data = SaveData {
        score,
        level,
        shots_until_drop,
        grid,
        timestamp: chrono::Utc::now().timestamp(),
    };
    serde_json::to_string(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON Error: {}", e)))
}

#[pyfunction]
fn deserialize_game_state(json_str: &str) -> PyResult<(Vec<Vec<Option<i32>>>, i64, u32, u32)> {
    let data: SaveData = serde_json::from_str(json_str)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("JSON Error: {}", e)))?;
    Ok((data.grid, data.score, data.level, data.shots_until_drop))
}

// ═══════════════════════════════════════════════
// DAFTAR FUNGSI YANG DIEKSPOR KE PYTHON
// ═══════════════════════════════════════════════

#[pymodule]
fn bubble_engine(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(find_matching, m)?)?;
    m.add_function(wrap_pyfunction!(find_floating_bubbles, m)?)?;
    m.add_function(wrap_pyfunction!(find_connected_cluster, m)?)?;
    m.add_function(wrap_pyfunction!(get_neighbors_list, m)?)?;
    m.add_function(wrap_pyfunction!(serialize_game_state, m)?)?;
    m.add_function(wrap_pyfunction!(deserialize_game_state, m)?)?;
    Ok(())
}
