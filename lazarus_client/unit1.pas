unit Unit1;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs,
  StdCtrls, ExtCtrls, ComCtrls, Buttons, Spin,
  TAGraph, TASeries, TAChartAxisUtils, TACustomSeries,
  LazSerial, fphttpclient, fpjson, jsonparser,
  Grids, Math;

const
  MAX_SAMPLES = 12;
  MAX_HIST    = 6;

type
  TdataArray = array[0..MAX_SAMPLES-1] of Integer;
  THistArray = array[0..MAX_HIST-1] of Integer;

  { TForm1 }
  TForm1 = class(TForm)
    // -- Serial
    MySerial: TLazSerial;
    // -- Timer UI
    tmrUI: TTimer;
    // -- Main chart (line series)
    ChartPM: TChart;
    SerieMP01: TLineSeries;
    SerieMP25: TLineSeries;
    SerieMP10: TLineSeries;
    // -- Histogram chart
    ChartHist: TChart;
    HistBar: TBarSeries;
    // -- Panel top
    pnlTop: TPanel;
    lblTitle: TLabel;
    // -- Panel COM
    pnlCom: TPanel;
    lblCOM: TLabel;
    edtCOM: TEdit;
    btnConnect: TBitBtn;
    // -- Panel UMA
    pnlUMA: TPanel;
    lblUMA: TLabel;
    cmbUMA: TComboBox;
    // -- Panel Flask
    pnlFlask: TPanel;
    lblFlask: TLabel;
    edtFlask: TEdit;
    chkSendFlask: TCheckBox;
    // -- Panel T/HR
    pnlTHR: TPanel;
    lblTE: TLabel;
    lblHR: TLabel;
    lblTEVal: TLabel;
    lblHRVal: TLabel;
    // -- Status
    pnlStatus: TPanel;
    lblStatus: TLabel;
    // -- Memo log
    memLog: TMemo;

    procedure FormCreate(Sender: TObject);
    procedure FormDestroy(Sender: TObject);
    procedure btnConnectClick(Sender: TObject);
    procedure MySerialRxData(Sender: TObject);
    procedure cmbUMAChange(Sender: TObject);
    procedure tmrUITimer(Sender: TObject);

  private
    // Data arrays
    aMP01 : TdataArray;
    aMP25 : TdataArray;
    aMP10 : TdataArray;
    aHisto: THistArray;
    aClr  : array[0..MAX_HIST-1] of TColor;
    // Seleccion UMA
    nUMA_Sel : Integer;
    sBufSerial: String;
    bConectado: Boolean;
    bNuevosDatos: Boolean;

    procedure InicializarArreglos;
    procedure ProcesarTrama(const sTrama: String);
    procedure ActualizarGrafica;
    procedure ActualizarHistograma;
    procedure LimpiarSeries;
    procedure Send_Data_To_Flask(nId: Integer; mp01,mp25,mp10,
                                  h03,h05,h10,h25,h50,h100,te,hr: Integer);
    procedure Log(const sMsg: String);
  public
  end;

var
  Form1: TForm1;

implementation

{$R *.lfm}

{ TForm1 }

procedure TForm1.FormCreate(Sender: TObject);
var
  i: Integer;
begin
  Caption := 'DataLogger - Contaminación Ambiental (UMA1-UMA5)';
  bConectado   := False;
  bNuevosDatos := False;
  sBufSerial   := '';
  nUMA_Sel     := 1;

  aClr[0] := clRed;
  aClr[1] := clFuchsia;
  aClr[2] := clBlue;
  aClr[3] := clGreen;
  aClr[4] := clYellow;
  aClr[5] := TColor($000099FF);

  InicializarArreglos;

  cmbUMA.Items.Clear;
  for i := 1 to 5 do
    cmbUMA.Items.Add('UMA' + IntToStr(i));
  cmbUMA.ItemIndex := 0;

  edtCOM.Text  := 'COM2';
  edtFlask.Text := 'http://127.0.0.1:5000/datos';

  lblStatus.Caption := 'Desconectado';
end;

procedure TForm1.FormDestroy(Sender: TObject);
begin
  if bConectado then
  begin
    MySerial.Active := False;
    bConectado := False;
  end;
end;

procedure TForm1.InicializarArreglos;
var
  i: Integer;
begin
  for i := 0 to MAX_SAMPLES-1 do
  begin
    aMP01[i] := 0;
    aMP25[i] := 0;
    aMP10[i] := 0;
  end;
  for i := 0 to MAX_HIST-1 do
    aHisto[i] := 0;
end;

procedure TForm1.Log(const sMsg: String);
begin
  if memLog.Lines.Count > 200 then
    memLog.Lines.Delete(0);
  memLog.Lines.Add(FormatDateTime('hh:nn:ss', Now) + ' ' + sMsg);
end;

procedure TForm1.btnConnectClick(Sender: TObject);
begin
  if not bConectado then
  begin
    try
      MySerial.Device   := edtCOM.Text;
      MySerial.BaudRate := br__9600;
      MySerial.DataBits := db8bits;
      MySerial.Parity   := pNone;
      MySerial.StopBits := sbOne;
      MySerial.FlowControl := fcNone;
      MySerial.Active   := True;
      bConectado := True;
      btnConnect.Caption := 'Desconectar';
      lblStatus.Caption  := 'Conectado a ' + edtCOM.Text;
      lblStatus.Font.Color := clGreen;
      Log('Conectado a ' + edtCOM.Text);
    except
      on E: Exception do
      begin
        ShowMessage('Error al conectar: ' + E.Message);
        Log('ERROR al conectar: ' + E.Message);
      end;
    end;
  end
  else
  begin
    MySerial.Active := False;
    bConectado := False;
    btnConnect.Caption := 'Conectar';
    lblStatus.Caption  := 'Desconectado';
    lblStatus.Font.Color := clRed;
    Log('Desconectado');
  end;
end;

procedure TForm1.MySerialRxData(Sender: TObject);
var
  sRecv: String;
  p: Integer;
begin
  sRecv := MySerial.ReadData;
  sBufSerial := sBufSerial + sRecv;

  repeat
    p := Pos(#10, sBufSerial);
    if p > 0 then
    begin
      ProcesarTrama(Trim(Copy(sBufSerial, 1, p - 1)));
      Delete(sBufSerial, 1, p);
    end;
  until p = 0;
end;

procedure TForm1.ProcesarTrama(const sTrama: String);
var
  aTokens: TStringList;
  nId, mp01, mp25, mp10: Integer;
  h03, h05, h10, h25, h50, h100, te, hr: Integer;
  i: Integer;
begin
  if sTrama = '' then Exit;

  aTokens := TStringList.Create;
  try
    aTokens.Delimiter := ',';
    aTokens.StrictDelimiter := True;
    aTokens.DelimitedText := sTrama;

    if aTokens.Count < 12 then Exit;

    nId  := StrToIntDef(aTokens[0],  0);
    mp01 := StrToIntDef(aTokens[1],  0);
    mp25 := StrToIntDef(aTokens[2],  0);
    mp10 := StrToIntDef(aTokens[3],  0);
    h03  := StrToIntDef(aTokens[4],  0);
    h05  := StrToIntDef(aTokens[5],  0);
    h10  := StrToIntDef(aTokens[6],  0);
    h25  := StrToIntDef(aTokens[7],  0);
    h50  := StrToIntDef(aTokens[8],  0);
    h100 := StrToIntDef(aTokens[9],  0);
    te   := StrToIntDef(aTokens[10], 0);
    hr   := StrToIntDef(aTokens[11], 0);

    if chkSendFlask.Checked then
      Send_Data_To_Flask(nId, mp01, mp25, mp10, h03, h05, h10, h25, h50, h100, te, hr);

    if nId <> nUMA_Sel then Exit;

    for i := 0 to MAX_SAMPLES-2 do
    begin
      aMP01[i] := aMP01[i+1];
      aMP25[i] := aMP25[i+1];
      aMP10[i] := aMP10[i+1];
    end;
    aMP01[MAX_SAMPLES-1] := mp01;
    aMP25[MAX_SAMPLES-1] := mp25;
    aMP10[MAX_SAMPLES-1] := mp10;

    aHisto[0] := h03;
    aHisto[1] := h05;
    aHisto[2] := h10;
    aHisto[3] := h25;
    aHisto[4] := h50;
    aHisto[5] := h100;

    lblTEVal.Caption := IntToStr(te) + ' °C';
    lblHRVal.Caption := IntToStr(hr) + ' %';

    bNuevosDatos := True;
    Log(Format('UMA%d | PM1:%d PM2.5:%d PM10:%d | T:%d H:%d', [nId,mp01,mp25,mp10,te,hr]));


  finally
    aTokens.Free;
  end;
end;

procedure TForm1.LimpiarSeries;
begin
  SerieMP01.Clear;
  SerieMP25.Clear;
  SerieMP10.Clear;
end;

procedure TForm1.ActualizarGrafica;
var
  i: Integer;
begin
  LimpiarSeries;
  for i := 0 to MAX_SAMPLES-1 do
  begin
    SerieMP01.AddXY(i, aMP01[i]);
    SerieMP25.AddXY(i, aMP25[i]);
    SerieMP10.AddXY(i, aMP10[i]);
  end;
end;

procedure TForm1.ActualizarHistograma;
var
  i: Integer;
  aLabels: array[0..5] of String = ('0.3','0.5','1.0','2.5','5.0','10');
begin
  HistBar.Clear;
  for i := 0 to MAX_HIST-1 do
    HistBar.Add(aHisto[i], aLabels[i], aClr[i]);
end;

procedure TForm1.tmrUITimer(Sender: TObject);
begin
  if bNuevosDatos then
  begin
    ActualizarGrafica;
    ActualizarHistograma;
    bNuevosDatos := False;
  end;
end;

procedure TForm1.cmbUMAChange(Sender: TObject);
begin
  nUMA_Sel := cmbUMA.ItemIndex + 1;
  InicializarArreglos;
  LimpiarSeries;
  Log('Cambiado a UMA' + IntToStr(nUMA_Sel));
end;

procedure TForm1.Send_Data_To_Flask(nId: Integer; mp01,mp25,mp10,
                                     h03,h05,h10,h25,h50,h100,te,hr: Integer);
var
  oHTTP  : TFPHTTPClient;
  jData  : TJSONObject;
  sJSON  : String;
  oStream: TStringStream;
begin
  oHTTP  := TFPHTTPClient.Create(nil);
  jData  := TJSONObject.Create;
  try
    jData.Add('id',   nId);
    jData.Add('mp01', mp01);
    jData.Add('mp25', mp25);
    jData.Add('mp10', mp10);
    jData.Add('h03',  h03);
    jData.Add('h05',  h05);
    jData.Add('h10',  h10);
    jData.Add('h25',  h25);
    jData.Add('h50',  h50);
    jData.Add('h100', h100);
    jData.Add('te',   te);
    jData.Add('hr',   hr);
    sJSON := jData.AsJSON;

    oHTTP.AddHeader('Content-Type','application/json');
    oStream := TStringStream.Create(sJSON);
    try
      oHTTP.RequestBody := oStream;
      oHTTP.Post(edtFlask.Text);
      Log('Flask OK: enviado ' + IntToStr(Length(sJSON)) + ' bytes');
    finally
      oStream.Free;
    end;
  except
    on E: Exception do
      Log('Flask ERROR: ' + E.Message);
  end;
  jData.Free;
  oHTTP.Free;
end;

end.
