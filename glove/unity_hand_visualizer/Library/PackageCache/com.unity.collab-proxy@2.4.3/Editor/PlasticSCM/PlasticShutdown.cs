using Codice.Client.Common.FsNodeReaders;
using Codice.CM.Common;
using Codice.LogWrapper;
using PlasticPipe.Client;

namespace Unity.PlasticSCM.Editor
{
    internal static class PlasticShutdown
    {
        internal static void Shutdown()
        {
            mLog.Debug("Shutdown");

            WorkspaceInfo wkInfo = FindWorkspace.InfoForApplicationPath(
                ApplicationDataPath.Get(), PlasticGui.Plastic.API);

            WorkspaceFsNodeReaderCachesCleaner.Shutdown();

            PlasticPlugin.Shutdown();
            PlasticApp.Dispose(wkInfo);

            ClientConnectionPool.Shutdown();
        }

        static readonly ILog mLog = PlasticApp.GetLogger("PlasticShutdown");
    }
}
