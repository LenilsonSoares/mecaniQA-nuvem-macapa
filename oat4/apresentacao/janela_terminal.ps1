<#
Abre esta janela do Windows PowerShell (chamada por capturar_prints.py via conhost.exe),
roda os comandos de verdade e salva um print SÓ desta janela (PrintWindow), sem
precisar que ela fique na frente das outras.

    conhost.exe powershell.exe -NoProfile -ExecutionPolicy Bypass -File janela_terminal.ps1 `
        -Pasta <pasta> -Arquivo <saida.png> -Comandos "docker compose ps||Get-Date"
#>
param(
    [Parameter(Mandatory)][string]$Pasta,
    [Parameter(Mandatory)][string]$Arquivo,
    [Parameter(Mandatory)][string]$Comandos,   # separados por ||
    [int]$Colunas = 112,
    [int]$Linhas = 16,
    [int]$Fonte = 20
)
$ErrorActionPreference = 'Stop'

Add-Type -ReferencedAssemblies System.Drawing @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class JanelaConsole {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct FONTE {
        public int cbSize; public int nFont; public short X; public short Y;
        public int Family; public int Weight;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)] public string Face;
    }
    public struct RETANGULO { public int Esq, Topo, Dir, Base; }

    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int h);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] static extern bool SetCurrentConsoleFontEx(IntPtr h, bool max, ref FONTE f);
    [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")] static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr h, out RETANGULO r);
    [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
    [DllImport("dwmapi.dll")] static extern int DwmGetWindowAttribute(IntPtr h, int atributo, out RETANGULO r, int tamanho);

    public static void Preparar(short altura) {
        SetProcessDPIAware();  // coordenadas em pixels reais da tela
        var f = new FONTE();
        f.cbSize = Marshal.SizeOf(f); f.Y = altura; f.Family = 54; f.Weight = 400; f.Face = "Consolas";
        SetCurrentConsoleFontEx(GetStdHandle(-11), false, ref f);
    }

    public static void Capturar(string arquivo) {
        IntPtr janela = GetConsoleWindow();
        RETANGULO total; GetWindowRect(janela, out total);
        // Borda visível (sem a sombra/borda invisível do Windows 10/11).
        RETANGULO visivel;
        bool temDwm = DwmGetWindowAttribute(janela, 9, out visivel, Marshal.SizeOf(typeof(RETANGULO))) == 0;
        using (var imagem = new Bitmap(total.Dir - total.Esq, total.Base - total.Topo)) {
            using (var g = Graphics.FromImage(imagem)) {
                IntPtr dc = g.GetHdc();
                PrintWindow(janela, dc, 2);  // PW_RENDERFULLCONTENT
                g.ReleaseHdc(dc);
            }
            var corte = temDwm
                ? new Rectangle(visivel.Esq - total.Esq, visivel.Topo - total.Topo, visivel.Dir - visivel.Esq, visivel.Base - visivel.Topo)
                : new Rectangle(0, 0, imagem.Width, imagem.Height);
            using (var recorte = imagem.Clone(corte, imagem.PixelFormat)) { recorte.Save(arquivo, ImageFormat.Png); }
        }
    }
}
"@

[JanelaConsole]::Preparar($Fonte)
$tela = $Host.UI.RawUI
$tela.WindowTitle = 'Windows PowerShell'
$maximo = $tela.MaxPhysicalWindowSize
$tamanho = New-Object Management.Automation.Host.Size([Math]::Min($Colunas, $maximo.Width), [Math]::Min($Linhas, $maximo.Height))
# Buffer do tamanho da janela: sem barra de rolagem no print.
$tela.WindowSize = New-Object Management.Automation.Host.Size(1, 1)
$tela.BufferSize = $tamanho
$tela.WindowSize = $tamanho

[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $Pasta
Clear-Host
foreach ($comando in $Comandos -split '\|\|') {
    Write-Host -NoNewline "PS $((Get-Location).Path)> "
    Write-Host $comando
    Invoke-Expression $comando | Out-Host
}
Write-Host -NoNewline "PS $((Get-Location).Path)> "
Start-Sleep -Milliseconds 800
[JanelaConsole]::Capturar($Arquivo)
