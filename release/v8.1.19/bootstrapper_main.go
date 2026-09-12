//go:build windows

package main

import (
    "archive/zip"
    "bytes"
    "embed"
    "fmt"
    "io"
    "os"
    "os/exec"
    "path/filepath"
    "strings"
    "syscall"
    "time"
    "unsafe"
)

const appVersion = "8.1.19"
const productName = "FieldBook Sync"

//go:embed payload.zip
var embeddedPayload embed.FS

func messageBox(title, text string, flags uintptr) {
    user32 := syscall.NewLazyDLL("user32.dll")
    proc := user32.NewProc("MessageBoxW")
    t, _ := syscall.UTF16PtrFromString(title)
    m, _ := syscall.UTF16PtrFromString(text)
    _, _, _ = proc.Call(0, uintptr(unsafe.Pointer(m)), uintptr(unsafe.Pointer(t)), flags)
}

func logPath() string {
    base := os.Getenv("LOCALAPPDATA")
    if strings.TrimSpace(base) == "" {
        base = os.TempDir()
    }
    dir := filepath.Join(base, "FieldBookSync", "logs")
    _ = os.MkdirAll(dir, 0755)
    return filepath.Join(dir, "setup_bootstrap.log")
}

func appendLog(path, msg string) {
    f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
    if err != nil {
        return
    }
    defer f.Close()
    stamp := time.Now().Format("2006-01-02 15:04:05.000")
    _, _ = fmt.Fprintf(f, "%s | %s\r\n", stamp, msg)
}

func fail(logFile, step string, err error) {
    msg := step
    if err != nil {
        msg += ": " + err.Error()
    }
    appendLog(logFile, "ERROR | "+msg)
    messageBox(productName+" Setup", msg+"\r\n\r\nThe installer did not modify your FieldBook Sync data.\r\n\r\nDiagnostic log:\r\n"+logFile, 0x00000010)
}

func extractZip(data []byte, dest string) error {
    zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data)))
    if err != nil {
        return fmt.Errorf("open embedded payload: %w", err)
    }
    cleanDest, err := filepath.Abs(dest)
    if err != nil {
        return err
    }
    prefix := cleanDest + string(os.PathSeparator)
    for _, zf := range zr.File {
        name := filepath.FromSlash(zf.Name)
        target := filepath.Join(cleanDest, name)
        absTarget, err := filepath.Abs(target)
        if err != nil {
            return err
        }
        if absTarget != cleanDest && !strings.HasPrefix(absTarget, prefix) {
            return fmt.Errorf("unsafe payload entry: %s", zf.Name)
        }
        if zf.FileInfo().IsDir() {
            if err := os.MkdirAll(absTarget, 0755); err != nil {
                return err
            }
            continue
        }
        if err := os.MkdirAll(filepath.Dir(absTarget), 0755); err != nil {
            return err
        }
        in, err := zf.Open()
        if err != nil {
            return err
        }
        out, err := os.OpenFile(absTarget, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
        if err != nil {
            in.Close()
            return err
        }
        _, copyErr := io.Copy(out, in)
        closeErr := out.Close()
        in.Close()
        if copyErr != nil {
            return copyErr
        }
        if closeErr != nil {
            return closeErr
        }
    }
    return nil
}

func powershellPath() string {
    if root := os.Getenv("SystemRoot"); root != "" {
        p := filepath.Join(root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        if _, err := os.Stat(p); err == nil {
            return p
        }
    }
    return "powershell.exe"
}

func main() {
    logFile := logPath()
    appendLog(logFile, "============================================================")
    appendLog(logFile, productName+" "+appVersion+" bootstrapper started")

    exePath, err := os.Executable()
    if err != nil {
        fail(logFile, "Could not determine the Setup EXE path", err)
        return
    }
    exePath, _ = filepath.Abs(exePath)
    appendLog(logFile, "SetupExe="+exePath)

    payloadBytes, err := embeddedPayload.ReadFile("payload.zip")
    if err != nil {
        fail(logFile, "Could not read the embedded installer payload", err)
        return
    }
    appendLog(logFile, fmt.Sprintf("Embedded payload bytes=%d", len(payloadBytes)))

    tempRoot, err := os.MkdirTemp("", "FieldBookSync_Setup_8_1_19_")
    if err != nil {
        fail(logFile, "Could not create the temporary setup folder", err)
        return
    }
    defer os.RemoveAll(tempRoot)
    payloadDir := filepath.Join(tempRoot, "payload")
    if err := os.MkdirAll(payloadDir, 0755); err != nil {
        fail(logFile, "Could not create the temporary payload folder", err)
        return
    }
    appendLog(logFile, "PayloadDir="+payloadDir)

    if err := extractZip(payloadBytes, payloadDir); err != nil {
        fail(logFile, "Could not extract the embedded FieldBook Sync files", err)
        return
    }
    appendLog(logFile, "Payload extraction completed")

    script := filepath.Join(payloadDir, "installer", "setup_ui.ps1")
    if _, err := os.Stat(script); err != nil {
        fail(logFile, "The setup wizard script is missing from the payload", err)
        return
    }

    ps := powershellPath()
    args := []string{
        "-NoLogo", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
        "-File", script,
        "-PayloadDir", payloadDir,
        "-SetupExe", exePath,
        "-Version", appVersion,
        "-BootstrapLog", logFile,
    }
    for _, a := range os.Args[1:] {
        if strings.EqualFold(strings.TrimSpace(a), "--uninstall") {
            args = append(args, "-Uninstall")
            break
        }
    }
    appendLog(logFile, "Launching setup wizard with "+ps)

    lf, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
    if err != nil {
        fail(logFile, "Could not open the setup diagnostic log", err)
        return
    }
    cmd := exec.Command(ps, args...)
    cmd.Stdout = lf
    cmd.Stderr = lf
    runErr := cmd.Run()
    lf.Close()

    if runErr != nil {
        if exitErr, ok := runErr.(*exec.ExitError); ok {
            fail(logFile, fmt.Sprintf("The setup wizard stopped with exit code %d", exitErr.ExitCode()), runErr)
        } else {
            fail(logFile, "The setup wizard could not be started", runErr)
        }
        return
    }
    appendLog(logFile, "Setup wizard exited normally")
}
