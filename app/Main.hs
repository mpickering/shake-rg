{-# LANGUAGE TypeApplications #-}
{-# LANGUAGE RecordWildCards #-}
{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE TypeFamilies #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
module Main where

import Development.Shake
import Development.Shake.Command
import Development.Shake.FilePath
import Development.Shake.Util

import Data.Aeson
import qualified Data.Map as M
import System.FilePath
import Data.Maybe
import System.IO.Temp
import System.Directory
import Data.Time.Clock
import Data.Time.Clock.POSIX
import Data.Typeable
import Data.Hashable
import Data.Binary (Binary)
import Control.DeepSeq

type RG2 = M.Map String (M.Map String Event)

data Event = Event { base_url :: String
                   , club :: String
                   , date :: String
                   , format :: Int
                   , kartatid :: Int
                   , map_url :: String
                   , mapfilename :: String
                   , mapid :: Int
                   , name :: String
                   , rawtype :: String
                   , worldfile :: WorldFile }

instance FromJSON Event where
  parseJSON =
    withObject "Event" $
      \v -> Event
              <$> v .: "base_url"
              <*> v .: "club"
              <*> v .: "date"
              <*> v .: "format"
              <*> v .: "kartatid"
              <*> v .: "map_url"
              <*> v .: "mapfilename"
              <*> v .: "mapid"
              <*> v .: "name"
              <*> v .: "rawtype"
              <*> v .: "worldfile"

instance ToJSON Event where
  toJSON Event{..} = object [ "base_url" .= base_url
                            , "club" .= club
                            , "date" .= date
                            , "format" .= format
                            , "kartatid" .= kartatid
                            , "map_url" .= map_url
                            , "mapfilename" .= mapfilename
                            , "mapid" .= mapid
                            , "name" .= name
                            , "rawtype" .= rawtype
                            , "worldfile" .= worldfile ]


data WorldFile = WorldFile { a,b,c, d,e,f :: Float
                           , valid :: Bool
                           , projection :: String
                           }


instance FromJSON WorldFile where
  parseJSON =
    withObject "WorldFile" $
      \v -> WorldFile
              <$> v .: "A"
              <*> v .: "B"
              <*> v .: "C"
              <*> v .: "D"
              <*> v .: "E"
              <*> v .: "F"
              <*> v .: "valid"
              <*> v .: "proj"

instance ToJSON WorldFile where
  toJSON WorldFile{..} = object [ "A" .= a, "B" .= b, "C" .= c, "D" .= d, "E" .= e, "F" .= f
                                , "valid" .= valid
                                , "proj" .= projection
                                ]



runScript :: FilePath -> [FilePath] -> Action ()
runScript script args = do
  need [script]
  cmd_ script args

newtype Age = Age Int  deriving (Show,Typeable,Eq,Hashable,Binary,NFData)
type instance RuleResult Age = Int


main :: IO ()
main = shakeArgs shakeOptions{shakeFiles="_build", shakeChange = ChangeModtimeAndDigest } $ do

    addOracle $ \(Age interval) -> ((`mod` interval) . round) <$> liftIO getPOSIXTime

    let parse_key path =
          let
            key = takeBaseName path
            (url, id)  = break (== '-') key
          in (url, tail id)

        mk_fp (url, id) ext = url ++ "-" ++ id <.> ext


    event_json <- newCache $ \file -> do
      either error id <$> (liftIO $ eitherDecodeFileStrict @RG2 file)

    merged_json <- newCache $ \file -> do
      need [file]
      either error id <$> (liftIO $ eitherDecodeFileStrict @(M.Map String [String]) file)

    let merged_vrts =
          map (<.> "vrt") . M.keys <$> merged_json "_build/merged/res.json"

    let need_vrts = do
           json <- event_json "_build/manifest.json"
           let all_with_world = M.map (M.filter (\e -> valid (worldfile e))) json
           let vrts = [ "_build/warp" </> mk_fp (url, id) "vrt" | (url, ids) <- M.assocs $ M.map M.keys all_with_world, id <- ids]
           need vrts
           return vrts

    phony "clean" $ do
        putInfo "Cleaning files in _build"
        removeFilesAfter "_build" ["//*"]

    phony "all"  $ do
      need ["_build/html/maps.html"]


    "_build/manifest.json" %> \out -> do
--        _ <- askOracle (Age 60 * 60 * 24)
       -- Rerun this once a day
        _ <- askOracle (Age $ 60 * 60 * 24)
        runScript "./scripts/scraper.py" [out, "new-world-files/"]


    -- Individual json files
    "_build/meta//*.json" %> \out -> do
      let (url, id) = parse_key out
      need ["_build/manifest.json"]
      json <- event_json "_build/manifest.json"
      let res = json M.! url M.! id
      liftIO $ encodeFile out res

    "_build/images//*.png" %> \out -> do
        let key = parse_key out
            meta = ("_build/meta" </> mk_fp key "json")

        need [meta]
        withTempDir $ \dir -> do
          runScript "./scripts/fetch.py" [dir, meta, "0" :: String]
          runScript "./scripts/convert_gif" [dir, takeDirectory out]

    -- VRT files
    "_build/warp//*.vrt" %> \out -> do
      let key = parse_key out
          img = "_build/images/" ++ mk_fp key "png"
          prj = "_build/images/" ++ mk_fp key "prj"
      need [img]
      runScript "./scripts/do_warp" [ out, img, prj]

    -- Merged rasters
    "_build/merged/res.json" %> \out -> do
      need ["_build/manifest.json"]
      vrts <- need_vrts
      runScript "./scripts/merge-rasters.py" (("_build/merged/") : vrts)

    "_build/merged/big.vrt" %> \out -> do
      need ["_build/merged/res.json"]

    "_build/merged/*.vrt" %> \out -> do
      let key = takeBaseName out
      need ["_build/merged/res.json"]

    -- This works incrementally so it won't really display the right things but
    -- for the big tiles it doesn't matter that much (and they take ~2 hours to generate).
    "_build/big-tiles/.big-stamp" %> \out -> do
      let big_vrt = "_build/merged/big.vrt"
      need [big_vrt]
      runScript "./scripts/make_big_tiles" ["-e", big_vrt, takeDirectory out]
      t <- liftIO $ getCurrentTime
      liftIO $ writeFile out (show t)

    "_build/small-tiles/**/*.stamp" %> \out -> do
      let key = takeBaseName out
          vrt = "_build/merged/" ++ key
      need [vrt]
      runScript "./scripts/make_tiles" [vrt, takeDirectory out, "16"]
      liftIO $ writeFile out key

    "_build/tiles/.stamp" %> \out -> do
        liftIO $ removeDirectoryRecursive "_build/tiles/"
        vrts <- merged_vrts
        let tile_dirs = ("_build/big-tiles/.big-stamp" : ["_build/small-tiles/" ++ vrt ++ "/" ++ vrt ++ ".stamp" | vrt <- vrts])
        need tile_dirs
        runScript "./scripts/symlink_join" ( takeDirectory out : map takeDirectory tile_dirs )
        liftIO $ writeFile out (unlines vrts)

    "_build/leaflet/maps.html" %> \out -> do
        need ["_build/manifest.json"]
        _ <- need_vrts
        runScript "./scripts/create-leaflet.py" ["_build/manifest.json", "_build/warp", "16", takeDirectory out]

    "_build/html/maps.html" %> \out -> do
        need ["_build/leaflet/maps.html"]
        need ["_build/tiles/.stamp"]
        runScript "./scripts/symlink_join" ( takeDirectory out : ["_build/tiles"] )
        liftIO $ copyFile "_build/leaflet/maps.html" out













--    "_build/images/*.pn


