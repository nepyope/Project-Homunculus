using UnityEngine;
using System;
using System.IO.Ports;
using System.Threading;

public class SerialController : MonoBehaviour
{
    private SerialPort serialPort;
    public string portName = "COM4";  // Change this to your port name
    public int baudRate = 9600;
    private Thread serialThread;
    private bool isRunning = true;
    public int[] sensorValues = new int[16];
    private string receivedData = "";

    void Start()
    {
        OpenSerialPort();
        StartSerialThread();
    }

    void OpenSerialPort()
    {
        try
        {
            serialPort = new SerialPort(portName, baudRate);
            serialPort.ReadTimeout = 1000;
            serialPort.Open();
            Debug.Log("Serial Port Opened");
        }
        catch (Exception e)
        {
            Debug.LogError("Failed to open serial port: " + e.Message);
        }
    }

    void StartSerialThread()
    {
        serialThread = new Thread(ReadSerialPort);
        serialThread.Start();
    }

    void ReadSerialPort()
    {
        while (isRunning)
        {
            try
            {
                string message = serialPort.ReadLine();
                receivedData = message;
                ProcessSerialData(message);
                Debug.Log("Received: " + message);
            }
            catch (TimeoutException)
            {
                // Ignore timeout exceptions
            }
            catch (Exception e)
            {
                Debug.LogError("Error reading from serial port: " + e.Message);
            }
        }
    }

    void ProcessSerialData(string data)
    {
        string[] values = data.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
        if (values.Length == 16)
        {
            for (int i = 0; i < values.Length; i++)
            {
                if (int.TryParse(values[i], out int result))
                {
                    sensorValues[i] = result;
                }
                else
                {
                    Debug.LogWarning("Invalid data format");
                }
            }
        }
        else
        {
            Debug.LogWarning("Unexpected data format");
        }
    }

    void OnApplicationQuit()
    {
        isRunning = false;
        if (serialThread != null && serialThread.IsAlive)
        {
            serialThread.Join();
        }

        if (serialPort != null && serialPort.IsOpen)
        {
            serialPort.Close();
            Debug.Log("Serial Port Closed");
        }
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 1000, 20), "Received Data: " + receivedData);
        for (int i = 0; i < sensorValues.Length; i++)
        {
            GUI.Label(new Rect(10, 30 + i * 20, 200, 20), $"Sensor {i + 1}: {sensorValues[i]}");
        }
    }
}
