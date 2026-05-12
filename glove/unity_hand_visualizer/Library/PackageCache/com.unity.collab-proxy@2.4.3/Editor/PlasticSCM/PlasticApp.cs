using System;
using System.IO;
using System.Linq;

using UnityEditor;
using UnityEngine;

using Codice.Client.BaseCommands;
using Codice.Client.Common;
using Codice.Client.Common.Connection;
using Codice.Client.Common.Encryption;
using Codice.Client.Common.EventTracking;
using Codice.Client.Common.FsNodeReaders;
using Codice.Client.Common.FsNodeReaders.Watcher;
using Codice.Client.Common.Threading;
using Codice.CM.Common;
using Codice.CM.ConfigureHelper;
using Codice.LogWrapper;
using Codice.Utils;
using CodiceApp.EventTracking;
using MacUI;
using PlasticGui;
using PlasticGui.EventTracking;
using PlasticGui.WebApi;
using PlasticPipe.Certificates;
using Unity.PlasticSCM.Editor.Configuration;
using Unity.PlasticSCM.Editor.UI;

namespace Unity.PlasticSCM.Editor
{
    internal static class PlasticApp
    {
        static PlasticApp()
        {
            RegisterDomainUnloadHandler();

            mLog = GetLogger("PlasticApp");
        }

        internal static ILog GetLogger(string name)
        {
            return LogManager.GetLogger(name);
        }

        internal static void InitializeIfNeeded()
        {
            if (mIsInitialized)
                return;

            mIsInitialized = true;

            ConfigureLogging();

            mLog.Debug("InitializeIfNeeded");

            if (!PlasticPlugin.IsUnitTesting)
                GuiMessage.Initialize(new UnityPlasticGuiMessage());

            RegisterExceptionHandlers();
            RegisterBeforeAssemblyReloadHandler();

            InitLocalization();

            if (!PlasticPlugin.IsUnitTesting)
                ThreadWaiter.Initialize(new UnityThreadWaiterBuilder());

            ServicePointConfigurator.ConfigureServicePoint();
            CertificateUi.RegisterHandler(new ChannelCertificateUiImpl());

            SetupFsWatcher();

            EditionManager.Get().DisableCapability(
                EnumEditionCapabilities.Extensions);

            ClientHandlers.Register();

            PlasticGuiConfig.SetConfigFile(
                PlasticGuiConfig.UNITY_GUI_CONFIG_FILE);

            if (!PlasticPlugin.IsUnitTesting)
            {
                mEventSenderScheduler = EventTracking.Configure(
                    (PlasticWebRestApi)PlasticGui.Plastic.WebRestAPI,
                    ApplicationIdentifier.UnityPackage,
                    IdentifyEventPlatform.Get());
            }

            if (mEventSenderScheduler != null)
            {
                UVCPackageVersion.AsyncGetVersion();

                mPingEventLoop = new PingEventLoop(
                    BuildGetEventExtraInfoFunction.ForPingEvent());
                mPingEventLoop.Start();
            }

            PlasticMethodExceptionHandling.InitializeAskCredentialsUi(
                new CredentialsUiImpl());
            ClientEncryptionServiceProvider.SetEncryptionPasswordProvider(
                new MissingEncryptionPasswordPromptHandler());
        }

        internal static void SetWorkspace(WorkspaceInfo wkInfo)
        {
            RegisterApplicationFocusHandlers();

            if (mEventSenderScheduler == null)
                return;

            mPingEventLoop.SetWorkspace(wkInfo);
            PlasticGui.Plastic.WebRestAPI.SetToken(
                CmConnection.Get().BuildWebApiTokenForCloudEditionDefaultUser());
        }

        internal static void EnableMonoFsWatcherIfNeeded()
        {
            if (PlatformIdentifier.IsMac())
                return;

            MonoFileSystemWatcher.IsEnabled = true;
        }

        internal static void DisableMonoFsWatcherIfNeeded()
        {
            if (PlatformIdentifier.IsMac())
                return;

            MonoFileSystemWatcher.IsEnabled = false;
        }

        internal static void Dispose(WorkspaceInfo wkInfo)
        {
            if (!mIsInitialized)
                return;

            try
            {
                mLog.Debug("Dispose");

                UnRegisterExceptionHandlers();
                UnRegisterApplicationFocusHandlers();

                if (mEventSenderScheduler != null)
                {
                    mPingEventLoop.Stop();
                    // Launching and forgetting to avoid a timeout when sending events files and no
                    // network connection is available.
                    // This will be refactored once a better mechanism to send event is in place
                    mEventSenderScheduler.EndAndSendEventsAsync();
                }

                if (wkInfo == null)
                    return;

                WorkspaceFsNodeReaderCachesCleaner.CleanWorkspaceFsNodeReader(wkInfo);
            }
            finally
            {
                mIsInitialized = false;
            }
        }

        static void RegisterDomainUnloadHandler()
        {
            AppDomain.CurrentDomain.DomainUnload += AppDomainUnload;
        }

        static void RegisterBeforeAssemblyReloadHandler()
        {
            AssemblyReloadEvents.beforeAssemblyReload += BeforeAssemblyReload;
        }

        static void RegisterApplicationFocusHandlers()
        {
            EditorWindowFocus.OnApplicationActivated += OnApplicationActivated;

            EditorWindowFocus.OnApplicationDeactivated += OnApplicationDeactivated;
        }

        static void RegisterExceptionHandlers()
        {
            AppDomain.CurrentDomain.UnhandledException += HandleUnhandledException;

            Application.logMessageReceivedThreaded += HandleLog;
        }

        static void UnRegisterDomainUnloadHandler()
        {
            AppDomain.CurrentDomain.DomainUnload -= AppDomainUnload;
        }

        static void UnRegisterBeforeAssemblyReloadHandler()
        {
            AssemblyReloadEvents.beforeAssemblyReload -= BeforeAssemblyReload;
        }

        static void UnRegisterApplicationFocusHandlers()
        {
            EditorWindowFocus.OnApplicationActivated -= OnApplicationActivated;

            EditorWindowFocus.OnApplicationDeactivated -= OnApplicationDeactivated;
        }

        static void UnRegisterExceptionHandlers()
        {
            AppDomain.CurrentDomain.UnhandledException -= HandleUnhandledException;

            Application.logMessageReceivedThreaded -= HandleLog;
        }

        static void AppDomainUnload(object sender, EventArgs e)
        {
            mLog.Debug("AppDomainUnload");

            UnRegisterDomainUnloadHandler();
        }

        static void HandleUnhandledException(object sender, UnhandledExceptionEventArgs args)
        {
            Exception ex = (Exception)args.ExceptionObject;

            if (IsExitGUIException(ex) ||
                !IsPlasticStackTrace(ex.StackTrace))
                throw ex;

            GUIActionRunner.RunGUIAction(delegate {
                ExceptionsHandler.HandleException("HandleUnhandledException", ex);
            });
        }

        static void HandleLog(string logString, string stackTrace, LogType type)
        {
            if (type != LogType.Exception)
                return;

            if (!IsPlasticStackTrace(stackTrace))
                return;

            GUIActionRunner.RunGUIAction(delegate {
                mLog.ErrorFormat("[HandleLog] Unexpected error: {0}", logString);
                mLog.DebugFormat("Stack trace: {0}", stackTrace);

                string message = logString;
                if (ExceptionsHandler.DumpStackTrace())
                    message += Environment.NewLine + stackTrace;

                GuiMessage.ShowError(message);
            });
        }

        static void OnApplicationActivated()
        {
            mLog.Debug("OnApplicationActivated");

            EnableMonoFsWatcherIfNeeded();
        }

        static void OnApplicationDeactivated()
        {
            mLog.Debug("OnApplicationDeactivated");

            DisableMonoFsWatcherIfNeeded();
        }

        static void BeforeAssemblyReload()
        {
            mLog.Debug("BeforeAssemblyReload");

            UnRegisterBeforeAssemblyReloadHandler();

            PlasticShutdown.Shutdown();
        }

        static void ConfigureLogging()
        {
            try
            {
                string log4netpath = ToolConfig.GetUnityPlasticLogConfigFile();

                if (!File.Exists(log4netpath))
                    WriteLogConfiguration.For(log4netpath);

                XmlConfigurator.Configure(new FileInfo(log4netpath));
            }
            catch
            {
                //it failed configuring the logging info; nothing to do.
            }
        }

        static void InitLocalization()
        {
            string language = null;
            try
            {
                language = ClientConfig.Get().GetLanguage();
            }
            catch
            {
                language = string.Empty;
            }

            Localization.Init(language);
            PlasticLocalization.SetLanguage(language);
        }
        
        static void SetupFsWatcher()
        {
            if (!PlatformIdentifier.IsMac())
                return;

            WorkspaceWatcherFsNodeReadersCache.Get().SetMacFsWatcherBuilder(
                new MacFsWatcherBuilder());
        }

        static bool IsPlasticStackTrace(string stackTrace)
        {
            if (stackTrace == null)
                return false;

            string[] namespaces = new[] {
                "Codice.",
                "GluonGui.",
                "PlasticGui."
            };

            return namespaces.Any(stackTrace.Contains);
        }

        static bool IsExitGUIException(Exception ex)
        {
            return ex is ExitGUIException;
        }

        static bool mIsInitialized;
        static EventSenderScheduler mEventSenderScheduler;
        static PingEventLoop mPingEventLoop;
        static ILog mLog;
    }
}