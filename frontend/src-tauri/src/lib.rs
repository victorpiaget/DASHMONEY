//! Coquille Tauri pour DashMoney Desktop.
//!
//! Au démarrage, on lance le sidecar `dashmoney-backend.exe` (FastAPI bundlé
//! via PyInstaller) en sous-process, et on le tue à la fermeture de la
//! fenêtre — sinon il continuerait à occuper le port 8000.
//!
//! En mode dev (`cargo tauri dev`), on cherche le binaire à
//! `<repo>/backend/dist/dashmoney-backend/dashmoney-backend.exe` en remontant
//! depuis le cwd jusqu'à trouver le marqueur `backend/desktop_main.py`.
//!
//! En mode bundle (tâche #9), on lira le binaire depuis le `resource_dir`
//! Tauri — pas encore implémenté ici.

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;

use tauri::{Manager, RunEvent};

/// Wrapper autour de l'enfant pour pouvoir le manager via l'app state.
struct SidecarChild(Mutex<Option<Child>>);

/// Localise le binaire du sidecar Python en mode dev.
///
/// On remonte depuis le cwd du processus Tauri jusqu'à trouver un dossier
/// qui contient `backend/desktop_main.py` (notre marqueur de racine projet).
fn locate_sidecar_dev() -> Result<PathBuf, String> {
    let cwd = std::env::current_dir().map_err(|e| format!("no cwd: {e}"))?;
    let project_root = cwd
        .ancestors()
        .find(|p| p.join("backend").join("desktop_main.py").exists())
        .ok_or_else(|| {
            format!(
                "Project root not found from cwd={}. \
                 Lance 'cargo tauri dev' depuis le dépôt DASHMONEY.",
                cwd.display()
            )
        })?
        .to_path_buf();

    let sidecar = project_root
        .join("backend")
        .join("dist")
        .join("dashmoney-backend")
        .join("dashmoney-backend.exe");

    if !sidecar.exists() {
        return Err(format!(
            "Sidecar non trouvé à {}. \
             Build manquant ? Lance d'abord : cd backend && poetry run pyinstaller desktop.spec --noconfirm",
            sidecar.display()
        ));
    }
    Ok(sidecar)
}

/// Localise le binaire du sidecar Python dans une version installée.
///
/// Le `bundle.resources` de tauri.conf.json copie le dossier
/// `backend/dist/dashmoney-backend/` dans `<resource_dir>/dashmoney-backend/`.
/// Le `resource_dir` pointe sur `<install_dir>/resources/` côté Windows.
fn locate_sidecar_bundled(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("resource_dir indisponible : {e}"))?;
    let sidecar = resource_dir
        .join("dashmoney-backend")
        .join("dashmoney-backend.exe");
    if !sidecar.exists() {
        return Err(format!(
            "Sidecar bundlé non trouvé à {}. \
             Le bundle.resources de tauri.conf.json est mal configuré.",
            sidecar.display()
        ));
    }
    Ok(sidecar)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let sidecar_state = SidecarChild(Mutex::new(None));

    let app = tauri::Builder::default()
        .manage(sidecar_state)
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Spawn du sidecar Python : chemin différent en dev vs bundled.
            // `cfg!(debug_assertions)` est true pour `cargo tauri dev`,
            // false pour `cargo tauri build` (release mode).
            let sidecar_path = if cfg!(debug_assertions) {
                locate_sidecar_dev()
            } else {
                locate_sidecar_bundled(&app.handle())
            }
            .map_err(|e| -> Box<dyn std::error::Error> { e.into() })?;

            eprintln!("[tauri] Launching sidecar: {}", sidecar_path.display());

            let child = Command::new(&sidecar_path)
                .spawn()
                .map_err(|e| -> Box<dyn std::error::Error> {
                    format!("Failed to spawn sidecar: {e}").into()
                })?;

            let state = app.state::<SidecarChild>();
            *state.0.lock().unwrap() = Some(child);

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            // Extraction dans un sous-scope pour relâcher le MutexGuard (et donc
            // le borrow sur `state`) avant la fin du callback — sinon le borrow
            // checker se plaint que `state` est dropped tant que le guard vit.
            let maybe_child = {
                let state = app_handle.state::<SidecarChild>();
                let extracted = state.0.lock().unwrap().take();
                extracted
            };
            if let Some(mut child) = maybe_child {
                eprintln!("[tauri] Killing sidecar (pid={})", child.id());
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    });
}
