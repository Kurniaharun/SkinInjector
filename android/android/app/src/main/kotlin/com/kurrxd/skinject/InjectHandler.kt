package com.kurrxd.skinject

import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import rikka.shizuku.Shizuku
import java.io.BufferedReader
import java.io.File
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

class InjectHandler(private val activity: MainActivity) : MethodChannel.MethodCallHandler {

    private val channelName = "com.kurrxd.skinject/inject"
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    private val shizukuListener = Shizuku.OnRequestPermissionResultListener { _, grantResult ->
        // permission result handled async
    }

    init {
        Shizuku.addRequestPermissionResultListener(shizukuListener)
    }

    fun register(messenger: io.flutter.plugin.common.BinaryMessenger) {
        MethodChannel(messenger, channelName).setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "hasRoot" -> executor.execute { reply(result, hasRoot()) }
            "hasShizuku" -> executor.execute { reply(result, hasShizuku()) }
            "requestShizukuPermission" -> {
                mainHandler.post {
                    try {
                        if (Shizuku.pingBinder()) {
                            if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
                                result.success(true)
                            } else {
                                Shizuku.requestPermission(1001)
                                result.success(Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED)
                            }
                        } else {
                            result.success(false)
                        }
                    } catch (e: Exception) {
                        result.success(false)
                    }
                }
            }
            "detectPackage" -> {
                @Suppress("UNCHECKED_CAST")
                val packages = call.argument<List<String>>("packages") ?: emptyList()
                executor.execute { reply(result, detectPackage(packages)) }
            }
            "preflight" -> {
                val mode = call.argument<String>("mode") ?: "auto"
                val pkg = call.argument<String>("package") ?: MLBB_PACKAGES[0]
                @Suppress("UNCHECKED_CAST")
                val packages = call.argument<List<String>>("packages") ?: MLBB_PACKAGES
                executor.execute {
                    reply(result, preflight(mode, pkg, packages))
                }
            }
            "injectSkin" -> {
                val url = call.argument<String>("downloadUrl") ?: ""
                val mode = call.argument<String>("mode") ?: "auto"
                val pkg = call.argument<String>("package") ?: MLBB_PACKAGES[0]
                executor.execute {
                    reply(result, injectSkin(url, mode, pkg))
                }
            }
            else -> result.notImplemented()
        }
    }

    private fun reply(result: MethodChannel.Result, value: Any?) {
        mainHandler.post { result.success(value) }
    }

    private fun hasRoot(): Boolean {
        return try {
            val p = Runtime.getRuntime().exec(arrayOf("su", "-c", "id"))
            val out = p.inputStream.bufferedReader().readText()
            p.waitFor()
            out.contains("uid=0")
        } catch (_: Exception) {
            false
        }
    }

    private fun hasShizuku(): Boolean {
        return try {
            Shizuku.pingBinder()
        } catch (_: Exception) {
            false
        }
    }

    private fun detectPackage(packages: List<String>): String? {
        for (pkg in packages) {
            if (isPackageInstalled(pkg)) return pkg
        }
        return null
    }

    private fun isPackageInstalled(pkg: String): Boolean {
        return try {
            val p = Runtime.getRuntime().exec(arrayOf("pm", "path", pkg))
            val out = p.inputStream.bufferedReader().readText()
            p.waitFor()
            out.contains("package:")
        } catch (_: Exception) {
            try {
                activity.packageManager.getPackageInfo(pkg, 0)
                true
            } catch (_: Exception) {
                false
            }
        }
    }

    private fun assetsPath(packageName: String): String {
        return "/storage/emulated/0/Android/data/$packageName/files/dragon2017/assets"
    }

    private fun preflight(mode: String, selectedPkg: String, packages: List<String>): Map<String, Any> {
        val messages = mutableListOf<String>()
        val pkg = if (isPackageInstalled(selectedPkg)) selectedPkg else detectPackage(packages) ?: selectedPkg
        if (!isPackageInstalled(pkg)) {
            messages.add("Mobile Legends tidak terdeteksi — install game dulu")
        }
        val path = assetsPath(pkg)
        val backend = pickBackend(mode, messages)
        val canWrite = backend != null && when (backend) {
            "shizuku" -> Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED &&
                testWrite(backend, path)
            else -> testWrite(backend, path)
        }
        val ok = backend != null && isPackageInstalled(pkg) && canWrite
        if (backend == null) {
            messages.add("Butuh Root (su) atau Shizuku untuk Android 11+")
        }
        return mapOf(
            "ok" to ok,
            "mode" to mode,
            "backend" to (backend ?: ""),
            "package" to pkg,
            "assetsPath" to path,
            "messages" to messages,
        )
    }

    private fun pickBackend(mode: String, messages: MutableList<String>): String? {
        val order = when (mode) {
            "root" -> listOf("root")
            "shizuku" -> listOf("shizuku")
            else -> buildList {
                if (hasRoot()) add("root")
                add("shizuku")
            }
        }
        for (name in order) {
            when (name) {
                "root" -> if (hasRoot()) {
                    messages.add("Backend: Root (su)")
                    return "root"
                } else messages.add("Root tidak tersedia")
                "shizuku" -> if (hasShizuku()) {
                    if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
                        messages.add("Backend: Shizuku")
                        return "shizuku"
                    }
                    messages.add("Shizuku terdeteksi — minta izin di pengaturan")
                    return "shizuku"
                } else messages.add("Shizuku tidak jalan")
            }
        }
        return null
    }

    private fun testWrite(backend: String, path: String): Boolean {
        val cmd = "test -w '${path}' && echo true || echo false"
        val out = runShell(backend, cmd)
        return out.contains("true")
    }

    private fun injectSkin(downloadUrl: String, mode: String, packageName: String): Map<String, Any> {
        if (downloadUrl.isBlank()) return mapOf("ok" to false, "message" to "URL download kosong")
        val messages = mutableListOf<String>()
        val backend = pickBackend(mode, messages) ?: return mapOf(
            "ok" to false,
            "message" to "Tidak ada akses Root/Shizuku",
        )
        if (backend == "shizuku" && Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) {
            return mapOf("ok" to false, "message" to "Izin Shizuku belum diberikan")
        }
        val target = assetsPath(packageName)
        val cacheDir = File(activity.cacheDir, "downloads")
        cacheDir.mkdirs()
        val zipFile = File(cacheDir, "IMB.zip")
        try {
            downloadFile(downloadUrl, zipFile)
            if (zipFile.length() < 1024) {
                return mapOf("ok" to false, "message" to "File ZIP terlalu kecil / invalid")
            }
            runShell(backend, "mkdir -p '${target}'")
            val unzip = "if unzip -o '${zipFile.absolutePath}' -d '${target}'; then echo true; else echo false; fi"
            val out = runShell(backend, unzip)
            zipFile.delete()
            return if (out.contains("true")) {
                mapOf("ok" to true, "message" to "Inject berhasil ke $target")
            } else {
                mapOf("ok" to false, "message" to "Unzip gagal: $out")
            }
        } catch (e: Exception) {
            zipFile.delete()
            return mapOf("ok" to false, "message" to "Error: ${e.message}")
        }
    }

    private fun downloadFile(urlStr: String, dest: File) {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.connectTimeout = 30000
        conn.readTimeout = 180000
        conn.setRequestProperty("User-Agent", "SkinJECT/1.0 KurrXd Flutter")
        conn.inputStream.use { input ->
            dest.outputStream().use { output -> input.copyTo(output) }
        }
    }

    private fun runShell(backend: String, inner: String): String {
        val cmd = when (backend) {
            "root" -> arrayOf("su", "-c", inner)
            "shizuku" -> {
                if (hasShizuku() && Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
                    return runShizukuShell(inner)
                }
                arrayOf("sh", "-c", inner)
            }
            else -> arrayOf("sh", "-c", inner)
        }
        return exec(cmd)
    }

    private fun runShizukuShell(inner: String): String {
        return try {
            val processClass = Class.forName("rikka.shizuku.Shizuku")
            val newProcessMethod = processClass.getMethod(
                "newProcess",
                Array<String>::class.java,
                Array<String>::class.java,
                String::class.java,
            )
            @Suppress("UNCHECKED_CAST")
            val process = newProcessMethod.invoke(null, arrayOf("sh", "-c", inner), null, null) as Process
            val out = process.inputStream.bufferedReader().readText()
            process.waitFor()
            out
        } catch (_: Exception) {
            exec(arrayOf("sh", "-c", inner))
        }
    }

    private fun exec(cmd: Array<String>): String {
        val p = Runtime.getRuntime().exec(cmd)
        val out = StringBuilder()
        BufferedReader(InputStreamReader(p.inputStream)).use { r ->
            var line: String?
            while (r.readLine().also { line = it } != null) out.append(line).append('\n')
        }
        p.waitFor()
        return out.toString()
    }

    companion object {
        val MLBB_PACKAGES = listOf(
            "com.mobile.legends",
            "com.vng.mlbbvn",
            "com.mobilelegends.hwag",
        )
    }
}
