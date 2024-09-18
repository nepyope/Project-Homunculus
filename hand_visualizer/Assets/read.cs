using UnityEngine;
using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Concurrent;

public class SerialController : MonoBehaviour
{
    private TcpClient tcpClient;
    private NetworkStream networkStream;
    public string ipAddress = "127.0.0.1"; // Localhost
    public int port = 65432; // Port the server is listening on
    private Thread networkThread;
    private volatile bool isRunning = true;
    public int[] sensorValues = new int[16];
    private string receivedData = "";

    // Use a thread-safe queue to communicate between threads
    private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

    void Start()
    {
        StartNetworkThread();
    }

    void StartNetworkThread()
    {
        networkThread = new Thread(ConnectToServer)
        {
            IsBackground = true
        };
        networkThread.Start();
    }

    void ConnectToServer()
    {
        try
        {
            tcpClient = new TcpClient();
            tcpClient.Connect(ipAddress, port);
            networkStream = tcpClient.GetStream();
            Debug.Log("Connected to the server");

            byte[] buffer = new byte[4096];

            while (isRunning)
            {
                try
                {
                    if (networkStream.DataAvailable)
                    {
                        int bytesRead = networkStream.Read(buffer, 0, buffer.Length);
                        if (bytesRead > 0)
                        {
                            string message = Encoding.UTF8.GetString(buffer, 0, bytesRead);
                            messageQueue.Enqueue(message);
                        }
                    }
                    else
                    {
                        Thread.Sleep(10); // Avoid busy waiting
                    }
                }
                catch (Exception e)
                {
                    Debug.LogError("Error reading from network stream: " + e.Message);
                    isRunning = false;
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError("Failed to connect to server: " + e.Message);
        }
    }

    void Update()
    {
        // Process messages from the queue on the main thread
        while (messageQueue.TryDequeue(out string message))
        {
            receivedData = message;
            ProcessNetworkData(message);
            Debug.Log("Received: " + message);
        }
    }

    void ProcessNetworkData(string data)
    {
        // Assuming the data is JSON formatted as in the Python script
        // Example: {"serial_data": "value1 value2 ... value16"}

        try
        {
            var jsonObject = JsonUtility.FromJson<SerialData>(data);
            string serialData = jsonObject.serial_data;
            string[] values = serialData.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);

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
                        Debug.LogWarning($"Invalid data format at index {i}: {values[i]}");
                    }
                }
            }
            else
            {
                Debug.LogWarning($"Unexpected data format: Expected 16 values, got {values.Length}");
            }
        }
        catch (Exception e)
        {
            Debug.LogError("Error processing network data: " + e.Message);
        }
    }

    void OnApplicationQuit()
    {
        isRunning = false;

        // Close the network stream and client
        networkStream?.Close();
        tcpClient?.Close();

        // Wait for the network thread to finish
        networkThread?.Join();

        Debug.Log("Disconnected from the server");
    }

    void OnGUI()
    {
        GUI.Label(new Rect(10, 10, 1000, 20), "Received Data: " + receivedData);
        for (int i = 0; i < sensorValues.Length; i++)
        {
            GUI.Label(new Rect(10, 30 + i * 20, 200, 20), $"Sensor {i + 1}: {sensorValues[i]}");
        }
    }

    [Serializable]
    private class SerialData
    {
        public string serial_data;
    }
}
